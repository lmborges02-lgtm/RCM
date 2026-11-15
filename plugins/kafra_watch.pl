package KafraWatch;
use strict;
use warnings;
use Plugins;
use Globals qw($char $field $net %jobs_lut);
use Network;
use Utils qw(calcPosition);
use JSON::PP qw(encode_json);
use Cwd qw(abs_path);
use File::Basename qw(dirname);
use File::Spec;
use Log ();

my $root = dirname(dirname(abs_path(__FILE__)));
my ($profile, $last, $started, $previous, $session, $warned) = ('', 0, 0, undef, '', '');
my ($delta, $earned) = (0, 0);
my (%items, %quotes, @events);
my $hooks;
Plugins::register('kafra_watch', 'Telemetria local para o Kafra Watch', \&unload);
$hooks = Plugins::addHooks(
    ['mainLoop_post', \&sample],
    ['packet/inventory_item_added', \&received],
    ['packet/npc_sell_list', \&quote_npc],
);

sub identity {
    no warnings 'once';
    my $id = $profiles::profile;
    return '' unless defined($id) && $id ne 'Use standard control folder' && $id =~ /\A[\p{L}\p{N} _.-]{1,100}\z/ && $id !~ /\A\.{1,2}\z/;
    return $id;
}
sub online { return $char && $net && eval { $net->getState() == Network::IN_GAME }; }
sub event {
    my ($type, $label) = @_;
    unshift @events, [$type, $label, time()];
    pop @events while @events > 30;
}
sub bind_profile {
    my $id = identity();
    return 0 unless length $id;
    if ($id ne $profile) {
        ($profile, $last, $started, $previous, $session, $delta, $earned) = ($id, 0, 0, undef, '', 0, 0);
        %items = (); @events = ();
    }
    return 1;
}
sub begin_session {
    $started = time();
    $session = join('-', $$, $started, int(rand(1_000_000)));
    $previous = defined $char->{zeny} ? 0 + $char->{zeny} : undef;
    $delta = $earned = 0;
    %items = (); @events = ();
    event('Conexão', 'Personagem entrou no mapa');
}
sub quote_npc {
    my (undef, $args) = @_;
    return unless bind_profile() && online() && defined $args->{itemsdata};
    my $raw = $args->{itemsdata};
    for (my $i = 0; $i + 10 <= length($raw); $i += 10) {
        my ($index, $base) = unpack('a2 V V', substr($raw, $i, 10));
        my $item = $char->inventory->getByID($index);
        next unless $item && $item->{nameID};
        next if keys(%quotes) >= 500 && !exists $quotes{$item->{nameID}};
        $quotes{$item->{nameID}} = [$base, time()];
    }
}
sub received {
    my (undef, $args) = @_;
    return unless bind_profile() && online() && $args->{item} && ($args->{amount} || 0) > 0;
    begin_session() unless $started;
    my $item = $args->{item};
    my $key = 0 + ($item->{nameID} || 0);
    return unless $key;
    return if !exists $items{$key} && keys(%items) >= 300;
    my $name = substr($item->{name} || "Item $key", 0, 120);
    my $kind = defined($item->{type}) && $item->{type} == 6 ? 'Carta' : 'Item';
    $items{$key} ||= [$name, $kind, 0, $key];
    $items{$key}[2] += $args->{amount};
    event('Coleta', "$name x$args->{amount}");
}
sub n { return defined($_[0]) && $_[0] =~ /\A-?\d+\z/ ? 0 + $_[0] : undef; }
sub sample {
    return unless bind_profile();
    my $now = time();
    return if $now - $last < 5;
    $last = $now;
    my $on = online();
    my $data = { profile => $profile, pid => $$, updated_at => $now, state => $on ? 'online' : 'offline' };
    $data->{quotes} = \%quotes;
    if ($on) {
        begin_session() unless $started;
        my $balance = n($char->{zeny});
        if (defined $balance && defined $previous) {
            my $diff = $balance - $previous;
            $delta += $diff;
            $earned += $diff if $diff > 0;
        }
        $previous = $balance;
        my $pos = eval { calcPosition($char) } || $char->{pos} || {};
        @$data{qw(name job base job_level hp maxhp sp maxsp zeny x y map width height)} = (
            substr($char->{name} || $profile, 0, 120), $jobs_lut{$char->{jobID} // -1} // '',
            map_stats($pos)
        );
        @$data{qw(session started_at gains net_zeny items events)} = (
            $session, $started, $earned, $delta, [sort { $b->[2] <=> $a->[2] } values %items], \@events
        );
    } elsif ($started) {
        event('Conexão', 'Sessão desconectada');
        $data->{events} = \@events;
        $started = 0;
    } else {
        $data->{events} = \@events;
    }
    my $path = File::Spec->catfile($root, 'logs', "kafra-watch-$profile-$$.json");
    my $tmp = "$path.tmp";
    my $ok = eval {
        open(my $fh, '>:raw', $tmp) or die "open: $!";
        print {$fh} encode_json($data) or die "write: $!";
        close $fh or die "close: $!";
        rename($tmp, $path) or die "rename: $!";
        1;
    };
    if (!$ok) {
        my $error = $@;
        Log::warning("[Kafra Watch] $error", 'plugins') if $error ne $warned;
        $warned = $error;
    } else { $warned = ''; }
}
sub map_stats {
    my ($pos) = @_;
    return (
        (map { n($char->{$_}) } qw(lv lv_job hp hp_max sp sp_max zeny)),
        n($pos->{x}), n($pos->{y}), ($field ? $field->baseName : ''),
        ($field ? $field->width : undef), ($field ? $field->height : undef)
    );
}
sub unload { Plugins::delHooks($hooks) if $hooks; }
1;

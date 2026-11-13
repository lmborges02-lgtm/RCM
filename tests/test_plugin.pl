use strict;
use warnings;
use File::Temp qw(tempdir);
use File::Path qw(make_path);
use File::Copy qw(copy);
use File::Spec;
use FindBin;
use JSON::PP;

# Simula somente as APIs do OpenKore, sem carregar um client real.
BEGIN {
    $INC{'Plugins.pm'} = 1;
    $INC{'Globals.pm'} = 1;
    $INC{'Network.pm'} = 1;
    $INC{'Log.pm'} = 1;
    package Plugins;
    sub register {}
    sub addHooks { return []; }
    sub delHooks {}
    package Globals;
    use Exporter 'import';
    our @EXPORT_OK = qw($net);
    our $net;
    package Network;
    use constant IN_GAME => 5;
    package Log;
    sub message {}
    sub warning { die $_[0]; }
}
use Globals qw($net);
{ package FakeNet; sub getState { $_[0]->{state} } }

my $root = tempdir(CLEANUP => 1);
make_path(File::Spec->catdir($root, 'plugins'), File::Spec->catdir($root, 'logs'));
my $source = File::Spec->catfile($FindBin::Bin, '..', 'plugins', 'rcm_status.pl');
my $plugin = File::Spec->catfile($root, 'plugins', 'rcm_status.pl');
copy($source, $plugin) or die "Cannot copy test plugin: $!";
$net = bless {state => 1}, 'FakeNet';
require $plugin;
sub snapshot {
    my $file = shift // 'rcm-status.json';
    open(my $fh, '<', File::Spec->catfile($root, 'logs', $file)) or die $!;
    local $/;
    return decode_json(<$fh>);
}
die 'Initial status was not written immediately' unless snapshot()->{state} eq 'offline';
die 'Initial offline should not allow recovery' if snapshot()->{recoverable};
$net->{state} = 5;
RCMStatus::state_changed();
die 'Online not detected' unless snapshot()->{state} eq 'online';
$net->{state} = 1;
RCMStatus::on_disconnect();
die 'Disconnect not detected' unless snapshot()->{state} eq 'offline' && snapshot()->{recoverable};
$profiles::profile = 'Conta01';
RCMStatus::state_changed();
die 'New profile inherited recovery' if snapshot('rcm-status-Conta01.json')->{recoverable};
$net->{state} = 5;
RCMStatus::state_changed();
$profiles::profile = 'Conta02';
$net->{state} = 1;
RCMStatus::on_disconnect();
die 'Wrong profile modified' unless snapshot('rcm-status-Conta01.json')->{state} eq 'online';
my $second = snapshot('rcm-status-Conta02.json');
die 'Profile disconnect not detected' unless $second->{state} eq 'offline' && $second->{recoverable};
die 'Legacy status modified' unless snapshot()->{recoverable};
RCMStatus::unload();
print "PASS: initial heartbeat, online, disconnect, replacement and unload\n";

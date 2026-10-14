package RCMStatus;
use strict;
use warnings;
use Plugins;
use Globals qw($net);
use Network;
use Time::HiRes qw(time);
use File::Basename qw(dirname);
use File::Spec;
use Cwd qw(abs_path);
use Log ();

# Não envia comandos ou pacotes ao jogo. Apenas observa o estado do OpenKore.
my $plugin_file = abs_path(__FILE__) or die '[RCM] Caminho do plugin indisponivel';
my $root = dirname(dirname($plugin_file));
my $path = File::Spec->catfile($root, 'logs', 'rcm-status.json');
my $last_write = 0;
my $ever_online = 0;
my $disconnected = 0;
my $sequence = 0;
my $hooks;
my $reported_error = '';
Plugins::register('rcm_status', 'Heartbeat local para Ragnarok Client Monitor', \&unload);
$hooks = Plugins::addHooks(
    ['mainLoop_post', \&heartbeat],
    ['Network::stateChanged', \&state_changed],
    ['disconnected', \&on_disconnect],
);
Log::message('[RCM] Plugin carregado. Status em: '.$path."\n", 'plugins');
heartbeat();

sub state_changed { $last_write = 0; heartbeat(); }
sub on_disconnect { $disconnected = 1; $last_write = 0; heartbeat(); }
sub heartbeat {
    my $now = time;
    return if $now - $last_write < 2;
    $last_write = $now;
    my $state = 'unknown';
    my $value = eval { $net->getState() };
    if (defined $value) {
        $state = ($value == Network::IN_GAME) ? 'online' : 'offline';
        if ($state eq 'online') { $ever_online = 1; $disconnected = 0; }
    }
    my $recoverable = ($state eq 'offline' && ($ever_online || $disconnected)) ? 'true' : 'false';
    $sequence++;
    my $json = '{"version":1,"writer_pid":'.$$.',"sequence":'.$sequence.',"updated_at":'.int($now).
               ',"state":"'.$state.'","recoverable":'.$recoverable.'}';
    my $temporary = $path . '.tmp';
    if (!open(my $out, '>', $temporary)) {
        report_error('Nao foi possivel criar o arquivo temporario: '.$!);
        return;
    } else {
        if (!print $out $json) { report_error('Falha ao gravar status: '.$!); close($out); return; }
        if (!close($out)) { report_error('Falha ao fechar status: '.$!); return; }
        if (!rename($temporary, $path)) { report_error('Falha ao atualizar status: '.$!); return; }
        if ($reported_error ne '') { Log::message("[RCM] Gravacao do status recuperada.\n", 'plugins'); }
        $reported_error = '';
        $last_write = $now;
    }
}
sub report_error {
    my ($text) = @_;
    if ($reported_error ne $text) { Log::warning('[RCM] '.$text."\n", 'plugins'); }
    $reported_error = $text;
}
sub unload {
    Plugins::delHooks($hooks) if $hooks;
    # A ausência de novas atualizações expira o status; não inventa uma desconexão.
}
1;

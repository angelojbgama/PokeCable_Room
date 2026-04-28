#!/bin/bash

if [ "$(id -u)" -ne 0 ]; then
    exec sudo "$0" "$@"
fi

CURR_TTY="/dev/tty1"
APP_NAME="PokeCable Room"
BASE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_DIR="$BASE_DIR/pokecable_room"
SCRIPT_NAME=$(basename "$0")
LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/launcher.log"
CLIENT_LOG="$LOG_DIR/client.log"
CONFIG_FILE="$APP_DIR/config.json"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

export TERM=linux
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

if command -v dialog >/dev/null 2>&1; then
    DIALOG_BIN="$(command -v dialog)"
elif command -v whiptail >/dev/null 2>&1; then
    DIALOG_BIN="$(command -v whiptail)"
else
    DIALOG_BIN=""
fi

dialog() {
    "$DIALOG_BIN" "$@"
}

ExitMenu() {
    printf "\033c" > "$CURR_TTY" 2>/dev/null || true
    printf "\e[?25h" > "$CURR_TTY" 2>/dev/null || true
    pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
    if [[ ! -e "/dev/input/by-path/platform-odroidgo2-joypad-event-joystick" ]]; then
        setfont /usr/share/consolefonts/Lat7-Terminus20x10.psf.gz 2>/dev/null || true
    fi
}

trap ExitMenu EXIT INT TERM

StartConsole() {
    printf "\033c" > "$CURR_TTY" 2>/dev/null || true
    printf "\e[?25l" > "$CURR_TTY" 2>/dev/null || true
    if [ -n "$DIALOG_BIN" ]; then
        dialog --clear > "$CURR_TTY" 2>/dev/null || true
    fi

    if [[ ! -e "/dev/input/by-path/platform-odroidgo2-joypad-event-joystick" ]]; then
        setfont /usr/share/consolefonts/Lat7-TerminusBold16.psf.gz 2>/dev/null || true
    else
        setfont /usr/share/consolefonts/Lat7-Terminus20x10.psf.gz 2>/dev/null || true
    fi

    pkill -9 -f gptokeyb 2>/dev/null || true
    pkill -9 -f osk.py 2>/dev/null || true

    if [ -e /dev/uinput ]; then
        chmod 666 /dev/uinput 2>/dev/null || true
    fi

    export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
    if [ -x /opt/inttools/gptokeyb ]; then
        /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "/opt/inttools/keys.gptk" > /dev/null 2>&1 &
    fi
}

MsgBox() {
    dialog --backtitle "$APP_NAME" --title "$1" --msgbox "$2" "${3:-10}" "${4:-70}" > "$CURR_TTY" 2>&1
}

InfoBox() {
    dialog --backtitle "$APP_NAME" --title "$1" --infobox "$2" "${3:-7}" "${4:-70}" > "$CURR_TTY" 2>&1
}

GenerateToken() {
    local length="${1:-4}"
    tr -dc 'a-z0-9' < /dev/urandom 2>/dev/null | head -c "$length"
}

ServerHostLabel() {
    GetServerUrl | sed 's#^wss://##; s#^ws://##; s#/ws$##'
}

RunClientWithDialog() {
    local title="$1"
    shift
    local run_log="$LOG_DIR/current-run.log"
    local pid
    local status
    local text

    : > "$run_log"
    "$@" > "$run_log" 2>> "$LOG_FILE" &
    pid=$!

    while kill -0 "$pid" 2>/dev/null; do
        text="$(tail -12 "$run_log" 2>/dev/null)"
        if [ -z "$text" ]; then
            text="Conectando ao servidor...\n\nSe voce criou a sala, deixe esta tela aberta e aguarde o outro usuario."
        fi
        dialog --backtitle "$APP_NAME" \
            --title "$title" \
            --infobox "$text\n\nAguardando... mantenha esta tela aberta." \
            18 76 > "$CURR_TTY" 2>&1
        sleep 1
    done

    wait "$pid"
    status=$?
    cat "$run_log" >> "$CLIENT_LOG" 2>/dev/null || true
    return "$status"
}

RequireRuntime() {
    if [ -z "$DIALOG_BIN" ]; then
        printf "\033c" > "$CURR_TTY"
        printf "Erro: dialog/whiptail nao esta instalado.\n" > "$CURR_TTY"
        sleep 5
        exit 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        MsgBox "Erro" "python3 nao foi encontrado no sistema." 8 60
        exit 1
    fi

    if [ ! -f "$APP_DIR/client.py" ]; then
        MsgBox "Erro" "client.py nao encontrado em:\n$APP_DIR" 9 70
        exit 1
    fi
}

EnsureLocalConfig() {
    python3 - "$CONFIG_FILE" "$APP_DIR/backups" "$LOG_DIR" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
backup_dir = sys.argv[2]
log_dir = sys.argv[3]
default = {
    "server_url": "wss://9kernel.vps-kinghost.net/ws",
    "default_save_dirs": ["/roms/gb", "/roms/gbc", "/roms/gba", "/roms/saves", "/roms2/gb", "/roms2/gbc", "/roms2/gba", "/roms2/saves"],
    "backup_dir": backup_dir,
    "log_dir": log_dir,
    "auto_trade_evolution": True,
    "item_trade_evolutions_enabled": False,
    "cross_generation": {
        "enabled": False,
        "enabled_modes": [],
        "policy": "safe_default",
        "unsafe_auto_confirm_data_loss": False,
    },
}
if path.exists():
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        default.update(loaded)
    except Exception:
        pass
default["backup_dir"] = backup_dir
default["log_dir"] = log_dir
default.pop("allow_cross_generation", None)
cross_generation = {
    "enabled": False,
    "enabled_modes": [],
    "policy": "safe_default",
    "unsafe_auto_confirm_data_loss": False,
}
cross_generation.update(default.get("cross_generation") or {})
if not cross_generation.get("enabled"):
    cross_generation["enabled_modes"] = []
default["cross_generation"] = cross_generation
path.write_text(json.dumps(default, indent=2), encoding="utf-8")
PY
}

GetServerUrl() {
    python3 - "$CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
default = "wss://9kernel.vps-kinghost.net/ws"
if not path.exists():
    print(default)
    raise SystemExit
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(default)
else:
    print(data.get("server_url") or default)
PY
}

SetServerUrl() {
    python3 - "$CONFIG_FILE" "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
server_url = sys.argv[2]
default = {
    "server_url": server_url,
    "default_save_dirs": ["/roms/gb", "/roms/gbc", "/roms/gba", "/roms/saves", "/roms2/gb", "/roms2/gbc", "/roms2/gba", "/roms2/saves"],
    "backup_dir": "/roms/tools/pokecable_room/backups",
    "log_dir": "/roms/tools/pokecable_room/logs",
    "auto_trade_evolution": True,
    "item_trade_evolutions_enabled": False,
    "cross_generation": {
        "enabled": False,
        "enabled_modes": [],
        "policy": "safe_default",
        "unsafe_auto_confirm_data_loss": False,
    },
}
if path.exists():
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        default.update(loaded)
    except Exception:
        pass
default["server_url"] = server_url
default.pop("allow_cross_generation", None)
cross_generation = {
    "enabled": False,
    "enabled_modes": [],
    "policy": "safe_default",
    "unsafe_auto_confirm_data_loss": False,
}
cross_generation.update(default.get("cross_generation") or {})
if not cross_generation.get("enabled"):
    cross_generation["enabled_modes"] = []
default["cross_generation"] = cross_generation
path.write_text(json.dumps(default, indent=2), encoding="utf-8")
PY
}

AskText() {
    local title="$1"
    local prompt="$2"
    local default="$3"
    VirtualKeyboard "$title" "$prompt" "$default" "text"
}

AskPassword() {
    local title="$1"
    local prompt="$2"
    VirtualKeyboard "$title" "$prompt" "" "password"
}

VirtualKeyboard() {
    local title="$1"
    local prompt="$2"
    local value="$3"
    local mode="$4"
    local choice
    local shown
    local chars=(
        "OK" "Confirmar"
        "DEL" "Apagar ultimo caractere"
        "SPACE" "Espaco"
        "CLEAR" "Limpar tudo"
        "a" "a" "b" "b" "c" "c" "d" "d" "e" "e" "f" "f" "g" "g" "h" "h" "i" "i" "j" "j"
        "k" "k" "l" "l" "m" "m" "n" "n" "o" "o" "p" "p" "q" "q" "r" "r" "s" "s" "t" "t"
        "u" "u" "v" "v" "w" "w" "x" "x" "y" "y" "z" "z"
        "A" "A" "B" "B" "C" "C" "D" "D" "E" "E" "F" "F" "G" "G" "H" "H" "I" "I" "J" "J"
        "K" "K" "L" "L" "M" "M" "N" "N" "O" "O" "P" "P" "Q" "Q" "R" "R" "S" "S" "T" "T"
        "U" "U" "V" "V" "W" "W" "X" "X" "Y" "Y" "Z" "Z"
        "0" "0" "1" "1" "2" "2" "3" "3" "4" "4" "5" "5" "6" "6" "7" "7" "8" "8" "9" "9"
        "-" "-" "_" "_" "." "." ":" ":" "/" "/" "@" "@"
    )

    while true; do
        if [ "$mode" = "password" ]; then
            shown="$(printf "%*s" "${#value}" "" | tr " " "*")"
        else
            shown="$value"
        fi

        choice=$(dialog --backtitle "$APP_NAME" \
            --title "$title" \
            --menu "$prompt\n\nValor: $shown\n\nUse D-pad e A. Escolha OK para confirmar." \
            22 74 14 \
            "${chars[@]}" \
            2>&1 > "$CURR_TTY") || return 1

        case "$choice" in
            "OK")
                printf "%s" "$value"
                return 0
                ;;
            "DEL")
                value="${value%?}"
                ;;
            "SPACE")
                value="${value} "
                ;;
            "CLEAR")
                value=""
                ;;
            *)
                value="${value}${choice}"
                ;;
        esac
    done
}

PrepareRoomCredentials() {
    local action="$1"
    local title="$2"
    local room=""
    local password=""
    local choice

    if [ "$action" = "create" ]; then
        room="poke-$(GenerateToken 4)"
        password="$(GenerateToken 6)"
        while true; do
            choice=$(dialog --backtitle "$APP_NAME" --title "$title" \
                --menu "Dados da sala\n\nSala: $room\nSenha: $password\nServidor: $(ServerHostLabel)\n\nPasse estes dados para o outro usuario." \
                18 76 5 \
                "Continue" "Criar sala com estes dados" \
                "Room" "Editar nome da sala" \
                "Password" "Editar senha" \
                "Random" "Gerar outro nome/senha" \
                "Cancel" "Cancelar" \
                2>&1 > "$CURR_TTY") || return 1
            case "$choice" in
                "Continue")
                    printf "%s\t%s" "$room" "$password"
                    return 0
                    ;;
                "Room")
                    room="$(AskText "$title" "Nome da sala:" "$room")" || return 1
                    ;;
                "Password")
                    password="$(AskText "$title" "Senha da sala:" "$password")" || return 1
                    ;;
                "Random")
                    room="poke-$(GenerateToken 4)"
                    password="$(GenerateToken 6)"
                    ;;
                *)
                    return 1
                    ;;
            esac
        done
    fi

    room="$(AskText "$title" "Nome da sala recebida:" "")" || return 1
    [ -z "$room" ] && return 1
    password="$(AskPassword "$title" "Senha da sala:")" || return 1
    [ -z "$password" ] && return 1
    printf "%s\t%s" "$room" "$password"
}

ChooseSave() {
    local tmp
    local choice
    tmp="$(mktemp)"
    find /roms /roms2 /opt/system/Tools "$BASE_DIR" -maxdepth 5 -type f \( -iname "*.sav" -o -iname "*.srm" \) ! -path "*/backups/*" -print 2>/dev/null | sort -u > "$tmp"
    if [ ! -s "$tmp" ]; then
        rm -f "$tmp"
        MsgBox "Save" "Nenhum .sav/.srm encontrado.\n\nCopie o save para /roms, /roms2 ou para a pasta da tool." 10 72
        return 1
    fi

    if [ "$(wc -l < "$tmp")" -eq 1 ]; then
        choice="$(cat "$tmp")"
        rm -f "$tmp"
        dialog --backtitle "$APP_NAME" --title "Save encontrado" \
            --yesno "Usar este save?\n\n$(basename "$choice")\n\nFeche o emulador antes de trocar." \
            12 72 > "$CURR_TTY" 2>&1 || return 1
        printf "%s" "$choice"
        return 0
    fi

    local menu_args=()
    local index=1
    local path
    while IFS= read -r path; do
        menu_args+=("$path" "$(basename "$path")")
        index=$((index + 1))
    done < "$tmp"
    rm -f "$tmp"

    choice=$(dialog --backtitle "$APP_NAME" --title "Escolher save" \
        --menu "Escolha o arquivo .sav/.srm local.\nFeche o emulador antes de trocar." \
        20 78 12 \
        "${menu_args[@]}" \
        2>&1 > "$CURR_TTY") || return 1
    printf "%s" "$choice"
}

ChoosePokemonFromSave() {
    local save_path="$1"
    local tmp
    local choice
    tmp="$(mktemp)"
    if ! python3 "$APP_DIR/client.py" --list-party --save "$save_path" > "$tmp" 2>> "$LOG_FILE"; then
        local err
        err="$(tail -30 "$LOG_FILE" 2>/dev/null)"
        rm -f "$tmp"
        MsgBox "Parser de save" "Nao foi possivel listar a party.\n\n$err" 18 76
        return 1
    fi

    local tsv
    tsv="$(mktemp)"
    python3 - "$tmp" > "$tsv" <<'PY'
import json
import sys
from pathlib import Path

party = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for item in party:
    if item["species_name"] == "Egg":
        continue
    label = f"{item['species_name']} Lv. {item['level']} ({item['nickname']})"
    print(f"{item['location']}\t{label}")
PY
    rm -f "$tmp"
    if [ ! -s "$tsv" ]; then
        rm -f "$tsv"
        MsgBox "Party" "Nenhum Pokemon encontrado na party." 8 60
        return 1
    fi

    local menu_args=()
    local location
    local label
    while IFS=$'\t' read -r location label; do
        menu_args+=("$location" "$label")
    done < "$tsv"
    rm -f "$tsv"

    choice=$(dialog --backtitle "$APP_NAME" --title "Escolher Pokemon" \
        --menu "Escolha o Pokemon da party para enviar.\nO recebido substituirá este slot com backup automatico." \
        20 78 12 \
        "${menu_args[@]}" \
        2>&1 > "$CURR_TTY") || return 1
    printf "%s" "$choice"
}

RunRealTrade() {
    local action="$1"
    local action_label="$2"
    local save_path
    local pokemon_location
    local server_url
    local room
    local password
    local credentials
    local status

    save_path="$(ChooseSave)" || return
    [ -z "$save_path" ] && return
    pokemon_location="$(ChoosePokemonFromSave "$save_path")" || return
    [ -z "$pokemon_location" ] && return

    server_url="$(GetServerUrl)"
    credentials="$(PrepareRoomCredentials "$action" "$action_label")" || return
    room="${credentials%%$'\t'*}"
    password="${credentials#*$'\t'}"

    dialog --backtitle "$APP_NAME" --title "Confirmar troca" \
        --yesno "Sala: $room\nSenha: $password\n\nSave:\n$(basename "$save_path")\nPokemon: $pokemon_location\n\nFeche o emulador antes de continuar.\nA tool criara backup antes de escrever.\n\nDepois que os dois usuarios oferecerem Pokemon, a troca sera confirmada automaticamente.\n\nContinuar?" \
        18 76 > "$CURR_TTY" 2>&1 || return

    RunClientWithDialog "$action_label" \
        python3 "$APP_DIR/client.py" \
        --action "$action" \
        --server "$server_url" \
        --room "$room" \
        --password "$password" \
        --save "$save_path" \
        --pokemon-location "$pokemon_location" \
        --auto-confirm
    status=$?

    if [ "$status" -eq 0 ]; then
        local output_text
        output_text="$(tail -12 "$LOG_DIR/current-run.log" 2>/dev/null)"
        MsgBox "Sucesso" "Troca aplicada.\n\n$output_text\n\nFeche a tool antes de abrir o jogo." 18 76
    else
        local tail_text
        tail_text="$(tail -35 "$LOG_DIR/current-run.log" "$LOG_FILE" 2>/dev/null)"
        MsgBox "Erro" "O client saiu com codigo $status.\n\nLog:\n$tail_text" 22 78
    fi
}

ConfigureServer() {
    local current
    local updated
    current="$(GetServerUrl)"
    updated="$(AskText "Servidor VPS" "URL WebSocket do servidor:" "$current")" || return
    [ -z "$updated" ] && return
    SetServerUrl "$updated"
    MsgBox "Servidor VPS" "Servidor configurado:\n$updated\n\nCross-generation permanece desativado." 10 72
}

HealthCheck() {
    local server_url
    local health_url
    local result
    server_url="$(GetServerUrl)"
    health_url="$(echo "$server_url" | sed 's#^wss://#https://#; s#^ws://#http://#; s#/ws$#/health#')"
    result="$(python3 - "$health_url" <<'PY'
import json
import sys
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=8) as response:
        print(response.read().decode("utf-8"))
except Exception as exc:
    print(f"ERROR: {exc}")
PY
)"
    MsgBox "Servidor" "URL:\n$server_url\n\nHealth:\n$health_url\n\nResposta:\n$result" 14 76
}

RestoreBackup() {
    local tmp
    local backup
    local metadata
    local destination
    tmp="$(mktemp)"
    find "$APP_DIR/backups" /roms/tools/pokecable_room/backups /opt/system/Tools/pokecable_room/backups \
        -maxdepth 1 -type f -name "*.bak" -print 2>/dev/null | sort -ru > "$tmp"
    if [ ! -s "$tmp" ]; then
        rm -f "$tmp"
        MsgBox "Backups" "Nenhum backup encontrado." 8 60
        return
    fi

    local menu_args=()
    local path
    while IFS= read -r path; do
        menu_args+=("$path" "$(basename "$path")")
    done < "$tmp"
    rm -f "$tmp"

    backup=$(dialog --backtitle "$APP_NAME" --title "Restaurar backup" \
        --menu "Escolha o backup para restaurar." \
        20 78 12 \
        "${menu_args[@]}" \
        2>&1 > "$CURR_TTY") || return

    metadata="${backup%.srm.bak}.metadata.json"
    if [ ! -f "$metadata" ]; then
        metadata="${backup%.sav.bak}.metadata.json"
    fi
    destination=""
    if [ -f "$metadata" ]; then
        destination="$(python3 - "$metadata" <<'PY'
import json
import sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("original_save", ""))
except Exception:
    print("")
PY
)"
    fi

    if [ -z "$destination" ]; then
        destination="$(ChooseSave)" || return
    fi

    dialog --backtitle "$APP_NAME" --title "Confirmar restore" \
        --yesno "Backup:\n$backup\n\nDestino:\n$destination\n\nIsto sobrescrevera o save de destino.\nContinuar?" \
        16 76 > "$CURR_TTY" 2>&1 || return

    cp "$backup" "$destination"
    MsgBox "Backup" "Backup restaurado em:\n$destination" 8 72
}

ToolsMenu() {
    local choice
    while true; do
        choice=$(dialog --backtitle "$APP_NAME" --title "Ferramentas" \
            --menu "Opcoes de manutencao." \
            17 72 6 \
            "Server" "Configurar servidor VPS" \
            "Health" "Testar conexao com servidor" \
            "Restore" "Restaurar backup" \
            "Logs" "Ver logs" \
            "About" "Sobre" \
            "Back" "Voltar" \
            2>&1 > "$CURR_TTY") || return
        case "$choice" in
            "Server") ConfigureServer ;;
            "Health") HealthCheck ;;
            "Restore") RestoreBackup ;;
            "Logs") ShowLogs ;;
            "About") About ;;
            *) return ;;
        esac
    done
}

ShowLogs() {
    local text
    text="launcher.log:\n$(tail -18 "$LOG_FILE" 2>/dev/null)\n\nclient.log:\n$(tail -18 "$CLIENT_LOG" 2>/dev/null)"
    dialog --backtitle "$APP_NAME" --title "Logs" --msgbox "$text" 24 78 > "$CURR_TTY" 2>&1
}

About() {
    MsgBox "PokeCable Room" \
"Produto inicial\n\nSuporte real atual:\n- Gen 1 Red/Blue/Yellow: party\n- Gen 2 Gold/Silver/Crystal: party\n- Gen 3 Ruby/Sapphire/Emerald/FireRed/LeafGreen: party\n- Backup automatico antes de escrever\n\nAinda nao implementado:\n- Boxes\n- Troca entre geracoes\n\nServidor:\n$(GetServerUrl)" 20 74
}

StartConsole
RequireRuntime
EnsureLocalConfig

while true; do
    CHOICE=$(dialog --backtitle "$APP_NAME" \
        --title "PokeCable Room" \
        --menu "Troca real por edicao segura de save\nGen 1, Gen 2 e Gen 3 ficam sempre separados.\nFeche o emulador antes de trocar.\nServidor: $(ServerHostLabel)" \
        16 72 5 \
        "CreateReal" "Criar troca" \
        "JoinReal" "Entrar em troca" \
        "Tools" "Ferramentas e backups" \
        "About" "Sobre" \
        "Exit" "Sair" \
        2>&1 > "$CURR_TTY")

    case "$CHOICE" in
        "CreateReal")
            RunRealTrade "create" "Criar sala"
            ;;
        "JoinReal")
            RunRealTrade "join" "Entrar em sala"
            ;;
        "Tools")
            ToolsMenu
            ;;
        "About")
            About
            ;;
        "Exit"|"")
            break
            ;;
    esac
done

exit 0

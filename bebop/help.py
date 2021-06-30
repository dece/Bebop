"""Help page. Currently only keybinds are shown as help."""

from bebop.config import DEFAULT_CONFIG

HELP_PAGE = """\
# Help

## Keybinds

Keybinds using the SHIFT key are written uppercase. Keybinds using the ALT (or META) key are written using the "M-" prefix. Keybinds using the CTRL key are written using the "C-" prefix. Symbol keys are written as their name, not the symbol itself.

* colon: focus the command-line
* r: reload page
* h (or left): scroll left a bit
* j (or down): scroll down a bit
* k (or up): scroll up a bit
* l (or right): scroll right a bit
* H: scroll left a whole page
* J (or page down): scroll down a whole page
* K (or page up): scroll up a whole page
* L: scroll right a whole page
* M-h: scroll one column left
* M-j: scroll one line down
* M-k: scroll one line up
* M-l: scroll one column right
* circumflex: horizontally scroll back to the first column
* gg: go to the top of the page
* G: go to the bottom of the page
* o: open an URL
* O: edit current URL
* M-o: open last download with an external command
* p: go to the previous page
* u: go to the parent page (up a level in URL)
* U: go to the root page (root URL for the current domain)
* b: open bookmarks
* B: add current page to bookmarks
* e: open the current page source in an editor
* y: open history
* digits: go to the corresponding link ID
* escape: reset status line text
* m: use another render mode for the current page
* slash (/): search for some text
* n: go to next search result
* N: go to previous search result
* C-c: cancel current operation

## Commands

Commands are mostly for actions requiring user input. You can type a command with arguments by pressing the corresponding keybind above.

* help: show this help page
* o(pen) <url>: open this URL
* q(uit): well, quit
* h(ome): open your home page
* i(nfo): show page informations
* forget-certificate <hostname>: remove saved fingerprint for this hostname
* set-render-mode: set render mode preference for the current URL
{plugin_commands}

## Configuration

Bebop uses a JSON file (usually in ~/.config). It is created with default values on first start. It is never written to afterwards: you can edit it when you want, just restart Bebop to take changes into account.

Here are the available options:

* command_editor (see note 1): command to use for editing cli input.
* connect_timeout (int): seconds before connection times out.
* download_path (string): download path.
* enabled_plugins: (see note 4): plugin names to load.
* external_command_default (see note 1): default command to open files.
* external_commands (see note 2): commands to open various files.
* generate_client_cert_command (see note 3): command to generate a client cert.
* history_limit (int): maximum entries in history.
* home (string): home page.
* list_item_bullet (string): text shown before every list item.
* persistent_history (bool): save and reload history.
* render_mode (string): default render mode to use ("fancy" or "dumb").
* scroll_step (int): number of lines/columns to scroll in one step.
* source_editor (see note 1): command to use for editing sources.
* text_width (int): rendered line length.

Notes:

1: For the "command" parameters such as source_editor and command_editor, a string list is used to separate the different program arguments, e.g. if you wish to use `vim -c 'startinsert'`, you should write the list `["vim", "-c", "startinsert"]`. In both case, a temporary or regular file name will be appended to this command when run.

2: The external_commands dict maps MIME types to commands just as above. For example, if you want to open video files with VLC and audio files in Clementine, you can use the following dict: `{{"audio": ["clementine"], "video": ["vlc"]}}`. For now only "main" MIME types are supported, i.e. you cannot specify precise types like "audio/flac", just "audio".

3: The generate_client_cert_command uses the same format as other commands (specified in note 1 above), with the exception that if the strings "{{cert_path}}", "{{key_path}}" or "{{common_name}}" are present in any string for the list, they will be replaced respectively by the certificate output path, the key output path and the CN to use.

4: The enabled_plugins list contain plugin names to load. Plugins are available if they are installed Python packages that can be imported using the `bebop_<plugin-name>` package name.

Your current configuration is:

{current_config}
"""


def get_help(config, plugins):
    plugin_commands = "\n".join(
        f"* {command.name}: {command.description}"
        for plugin in plugins
        for command in plugin.commands
    )
    config_list = "\n".join(
        (
            f"* {key} = {config[key]} (default {repr(DEFAULT_CONFIG[key])})"
            if config[key] != DEFAULT_CONFIG[key]
            else f"* {key} = {config[key]}"
        )
        for key in sorted(config)
    )
    return HELP_PAGE.format(
        plugin_commands=plugin_commands,
        current_config=config_list
    )

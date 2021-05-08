Bebop
=====

Bebop is a [Gemini][gemini] browser for the terminal, focusing on practicality
and speed. It is a personal project to learn how to use ncurses and try new
ways to explore the Geminispace. It borrows some ideas from [Amfora][amfora],
another great terminal browser, Vim for interactivity and tries to support mouse
usage decently.

[gemini]: https://gemini.circumlunar.space/
[amfora]: https://github.com/makeworld-the-better-one/amfora

If you are interested in Gemini and looking for a desktop/laptop client, I
recommend trying a graphical one like the excellent [Lagrange][lagrange] or
[Kristall][kristall], or Amfora if you're feeling more at home in the terminal.
Bebop won't attempt to support every feature other clients might have.

[lagrange]: https://git.skyjake.fi/skyjake/lagrange
[kristall]: https://kristall.random-projects.net/

It passes the Conman's client test but not Egsam's for now.



Features
--------

Why use Bebop instead of something else?

### Lightweight

It does not use any external dependencies. Everything including NCurses or TLS
is done using Python's standard library.

### Nice keybinds

A lot of keybinds are defined, and Vim users should get quickly familiar with
them. Find them in the help page by pressing `?`.

### Fun

Link navigation is done by entering the link ID with automatic validation: if
there are less than 10 links on a page, pressing the link ID will take you to
the page directly. If there are 30 links, pressing "1" will wait for another
digit. If there are 1000 links but you wish to visit link #5, pressing 5 and
enter will do!

Of course this is based on my own perception of what exactly makes a client
"fun" to use, but give it a shot!

### And more!

It does not try to do many things. Common basic browsing features work: go to
URL, scrolling, follow links, redirections, page encodings, etc.

It also provide these features:

- History
- Caching
- Bookmarks (it's just a text file with bindings)
- Downloads

Check out [this board](BOARD.txt) for what's done and coming next.



Configuration
-------------

Bebop uses a JSON file (usually in `~/.config`). It is created with default
values on first start. It is never written to afterwards: you can edit it when
you want, just restart Bebop to take changes into account.

Here are the available options:

| Key                        | Type         | Default        | Description                           |
|----------------------------|--------------|----------------|---------------------------------------|
| `connect_timeout`          | int          | 10             | Seconds before connection times out.  |
| `text_width`               | int          | 80             | Rendered line length.                 |
| `source_editor`            | string list  | `["vi"]`       | Command to use for editing sources.   |
| `command_editor`           | string list  | `["vi"]`       | Command to use for editing CLI input. |
| `external_commands`        | (see note 2) | {}             | Commands to open various files.       |
| `external_command_default` | string list  | `["xdg-open"]` | Default command to open files.        |

Note: for the "command" parameters such as `source_editor` and `command_editor`,
a string list is used to separate the different program arguments, e.g. if you
wish to use `vim -c 'startinsert'`, you should write the list `["vim", "-c",
"startinsert"]`. In both case, a temporary or regular file name will be appended
to this command when run.

2: the `external_commands` dict maps MIME types to commands just as above. For
example, if you want to open video files with VLC and audio files in Clementine,
you can use the following dict: `{"audio": ["clementine"], "video", ["vlc"]}`.
For now only "main" MIME types are supported, i.e. you cannot specify precise
types like "audio/flac", just "audio".



FAQ
---

### Can I change the colors?

I do not plan to allow modifying the colors or elements style for now. Configure
a nice palette for your terminal so that Bebop fits nicely in there!

### Will Bebop implement subscriptions?

I have no need for them as I prefer to use a browser-agnostic aggregator at the
moment, so no.

### WTF is wrong with the command line?

I don't understand how you're supposed to create a fine input field in pure
curses without the form extension library, which is not available from Python.
Or, I think I understand but it's way too hard for the limited time I have to
work on Bebop. So the command line is based on the very limited Textbox class;
it's fine for entering a simple URL or a bookmark title but if you need to type
more than the window's width, press `M-e` (ALT + e) to open an editor.

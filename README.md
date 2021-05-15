Bebop
=====

Bebop is a [Gemini][gemini] browser for the terminal, focusing on practicality
and laziness. It is a personal project to learn how to use ncurses and try new
ways to explore the Geminispace. It borrows some ideas from [Amfora][amfora],
another great terminal browser, Vim for interactivity and tries to support mouse
usage decently.

[gemini]: https://gemini.circumlunar.space/
[amfora]: https://github.com/makeworld-the-better-one/amfora

If you are interested in Gemini and looking for a desktop/laptop client, I
recommend trying a graphical one like the excellent [Lagrange][lagrange] or
[Kristall][kristall], or Amfora if you're feeling more at home in the terminal.
Bebop won't attempt to support every feature other clients might have, but if
you want to try something a bit different, keep reading…

[lagrange]: https://git.skyjake.fi/skyjake/lagrange
[kristall]: https://kristall.random-projects.net/



Features
--------

Why use Bebop instead of something else?

- Lightweight, no external Python dependencies.
- Nice keybinds are defined, and Vim users should get quickly familiar with
    them.
- Fun! Link navigation is done by entering the link ID with automatic
    validation: if there are less than 10 links on a page, pressing the link ID
    will take you to the page directly. If there are 30 links, pressing "1" will
    wait for another digit. If there are 1000 links but you wish to visit link
    5, pressing 5 and enter will do. Of course this is based on my own
    perception of what exactly makes a client "fun" to use, but give it a shot!
- History, cache, client certificates, bookmarks (it's just a text file with
    bindings), downloads and more!

You can check out the Bebop page on Gemini at gemini://dece.space/dev/bebop.gmi,
or [this board](BOARD.txt) for what's done and what might be cooking.



Install
-------

TODO



Usage
-----

Just run `bebop`, optionally following by an URL.

Documentation about the keybinds, config values and commands are embed into the
software itself: press "?" to display the help page.

Happy browsing!

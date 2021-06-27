Architecture
============

This document is for people who want to get an overview of the Bebop code and
the way things work. These are high-level views, more details are given in the
respective modules' docstrings.



Events
------

There are no event loop dispatching actions asynchronously, everything runs in a
single thread. The UI waits for user input and reacts on them.

In the future we may decouple the UI from the core browser to allow background
downloads and streaming content.



Rendering
---------

A core element of Bebop is what I call "metalines", which are lines of text as
they are rendered on screen, along with specific line metadata. Metalines are
rendered directly on screen, so they are not wrapped, cut or whatever: they
already represent formatted text as it will be shown. They carry information
such as line type (i.e. is this line part of a link, a title, etc), and more
specific data such as target URLs for link lines.

Rendering from the server response to showing content in the curses UI takes
several steps:

1. Parse the response from the server. If it's successful and a text MIME type
   is provided, use it to parse the response content.
2. Response parsing can directly produce metalines (e.g. from `text/plain`) or
   have intermediate parsing steps: a `text/gemini` document is first parsed
   into a list of gemtext "elements" (paragraphs, links, etc), and converting
   those elements into metalines happen in a following step. This lets Bebop
   separate gemtext semantics from the way it is rendered, thus using the
   desired wrapping and margins.
3. Metalines are rendered on the screen, with the colors and attributes
   matching the line type.



Plugins
-------

The plugin interface is improved only when there is demand for something; for
now it only supports plugins that can handle new schemes.

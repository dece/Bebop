Gopher plugin for Bebop
=======================

This is a Gopher plugin for [Bebop][bebop], refer to its docs for details.

[bebop]: https://git.dece.space/Dece/Bebop

Requires:

* Bebop >= 0.2.0

It currently displays only the maps and the file item types.

Avoid using the path navigation features of Bebop because they do not make much
sense in Gopher; Gopher URLs do not really represent a path as they can be
prefixed with an item type, so going up one level from a file item will usually
put you on a map item with the file item indicator still in the URL. Going to
the root URL and history navigation should still be fine though.

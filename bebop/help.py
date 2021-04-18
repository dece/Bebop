"""Help page. Currently only keybinds are shown as help."""

HELP_PAGE = """\
# Bebop keybinds

Keybinds using the SHIFT key are written uppercase. Keybinds using the ALT (or \
META) key are written using the "M-" prefix. Symbol keys are written as their \
name, not the symbol itself.

``` list of bebop keybinds
- colon: focus the command-line
- r: reload page
- h: scroll left a bit
- j: scroll down a bit
- k: scroll up a bit
- l: scroll right a bit
- H: scroll left a whole page
- J: scroll down a whole page
- K: scroll up a whole page
- L: scroll right a whole page
- M-h: scroll one column left
- M-j: scroll one line down
- M-k: scroll one line up
- M-l: scroll one column right
- circumflex: horizontally scroll back to the first column
- gg: go to the top of the page
- G: go to the bottom of the page
- o: open an URL
- p: go to the previous page
- u: go to the parent page (up a level in URL)
- U: go to the root page (root URL for the current domain)
- b: open bookmarks
- B: add current page to bookmarks
- e: open the current page source in an editor
- digits: go to the corresponding link ID
- escape: reset status line text
```
"""

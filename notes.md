# NOTES

## RESOURCES

- https://tetracorp.github.io/tokimeki-memorial/data/user-defined-labels.html
  Intersting document with some function naming

## TODOS:

- Figure out how palettes and how graphics are loaded to improve the nbn editor

- Work on text extraction

## IMAGES

- Images are stored in CDROM/\*.NBN, figured it out with tilemolester. I'm working on an editor to make graphics editing
  easier for translators. An easily viewable modification is in CDROM/FUKUTEST/TITLE.NBN, containing the graphics data
  present on the title menu.

## TEXT

- TODO

## REVERSE ENGINEERING

- Interesting functions
  8009f99c : graphics setup + VRAM loading
  8004ebb0 : Dialog (TODO)
  800689fc : cal_font_load (TODO)
  80069384 : cal_sprite_init (TODO)

- 8008a854 has references to Cd_read. After this call, something is loaded to VRAM. (VERIFY)
  Interestingly, this does not get called to load the video, but only to load the cutscene stuff.
  First thing to get loaded is the palette. From where??

  After the call to 800b4020, iVar2 is set to 0x279, after it adds 0x1e0 and becomes 0x459
  iVar2 then gets set to the result of 8008a004 passed with 1 and auStack_28

  What I imagine happened:
  function: load_data_to_vram_possible (8008a854), calls load_from_cd_ready_possible -> which calls load_cd_sync_possible
  once the CF is ready, it performs some checks, and then calls:
  iVar2 = FUN_8008a1f8 -> investigate this
  afterwards it checks if iVar2 == 0 and, if it is, it performs some operations on DAT_800e2df0 and returns DAT_800e2dec
  else it returns -1 (likely failed)

  In the case of the palette loading, it seems to go into iVar2 == 0 if statement

- Going up the call stack we get to 80087e2c, which calls 8008ad58, which calls load_data_to_vram_possible
  80087e2c gets called by FUN_800457fc
  800b4164 seems to handle vsync

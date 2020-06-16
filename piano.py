import time
import sys
import pygame
from mingus.containers import Note as _Note
from mingus.midi import fluidsynth


class Note(_Note):
    def __hash__(self):
        return int(self)


SF2 = "Salamander-UltraCompact-JNv3.0.sf2"
# SF2 = "Nice-Steinways-JNv5.8.sf2"
# SF2 = "Yamaha-C5-Salamander-JNv5.1.sf2"
# RECORD_FILE = "record.wav"
RECORD_FILE = None
OCTAVES = 5  # number of octaves to show
LOWEST = 2  # lowest octave to show
VISUAL_FADEOUT = 0.25  # coloration fadeout time (1 tick = 0.001)
NOTE_STOP_TIMEOUT = 0.03
WHITE_KEYS = ["C", "D", "E", "F", "G", "A", "B"]
BLACK_KEYS = ["C#", "D#", "F#", "G#", "A#"]


if RECORD_FILE is not None:
    fluidsynth.midi.start_recording(RECORD_FILE)
fluidsynth.midi.start_audio_output()

if not fluidsynth.midi.load_sound_font(SF2):
    print("Couldn't load soundfont", SF2)
    sys.exit(1)
fluidsynth.midi.fs.program_reset()
fluidsynth.initialized = True

pygame.init()
pygame.font.init()
font = pygame.font.SysFont("monospace", 12)
pygame.display.init()

key_graphic = pygame.image.load("keys.png")
kgrect = key_graphic.get_rect()
(width, height) = (kgrect.width, kgrect.height)
white_key_width = width / 7

# Reset display to wrap around the keyboard image

screen = pygame.display.set_mode((OCTAVES * width, height))

if key_graphic.get_alpha() is None:
    image = key_graphic.convert()
else:
    image = key_graphic.convert_alpha()

pygame.display.set_caption("mingus piano")
current_octave = 3
current_channel = 8

# pressed is a surface that is used to show where a key has been pressed

pressed = pygame.Surface((white_key_width, height))
pressed.fill((0, 230, 0))


class NoteCtl:
    def __init__(self):
        self.note_states = {}
        self._note_visual_offsets = {}
        self.start_time = None
        self._tick = 0.0

    def play_note(self, note_name, octave):
        """play_note determines the coordinates of a note on the keyboard image
        and sends a request to play the note to the fluidsynth server"""
        note = Note(note_name, octave)

        self.note_states[note] = self._tick, None

        # Play the note
        if self.start_time is None:
            self.start_time = time.time()

        fluidsynth.play_Note(note, current_channel, 100)

    def stop_note(self, note_name, octave):
        note_to_stop = Note(note_name, octave)
        start_t, _ = self.note_states[note_to_stop]
        self.note_states[note_to_stop] = start_t, self._tick

    def tick(self):
        self._tick += 0.001
        to_delete = []
        for note, (start_t, end_t) in self.note_states.items():
            diff = self._tick - start_t
            if diff < VISUAL_FADEOUT:
                w = self._get_visual_offset(note)
                if note.name in WHITE_KEYS:
                    pressed.fill(
                        (0, ((VISUAL_FADEOUT - diff) / VISUAL_FADEOUT) * 255, 124)
                    )
                    screen.blit(pressed, (w, 0), None, pygame.BLEND_SUB)
                else:
                    pressed.fill(
                        (((VISUAL_FADEOUT - diff) / VISUAL_FADEOUT) * 125, 0, 125)
                    )
                    screen.blit(pressed, (w, 1), (0, 0, 19, 68), pygame.BLEND_ADD)
            if end_t is not None and (self._tick - end_t) > NOTE_STOP_TIMEOUT:
                fluidsynth.stop_Note(note, current_channel)
                to_delete.append(note)
        for note in to_delete:
            del self.note_states[note]

    def _get_visual_offset(self, note):
        if note not in self._note_visual_offsets:
            octave_offset = (note.octave - LOWEST) * width
            if note.name in WHITE_KEYS:
                w = WHITE_KEYS.index(note.name) * white_key_width
                w = w + octave_offset
            else:
                i = BLACK_KEYS.index(note.name)
                if i == 0:
                    w = 18
                elif i == 1:
                    w = 58
                elif i == 2:
                    w = 115
                elif i == 3:
                    w = 151
                else:
                    w = 187
                w = w + octave_offset
            self._note_visual_offsets[note] = w
        return self._note_visual_offsets[note]


note_ctl = NoteCtl()


keyboard_layout = [
    ("asdfghjkl;'\\", "`zxcvbnm,./"),
    ("1234567890-=\b", "\tqwertyuiop[]\r"),
]

key_mapping = {}
for octave_shift, (black_line, white_line) in enumerate(keyboard_layout):
    for i, c in enumerate(white_line):
        key_mapping[ord(c)] = (
            WHITE_KEYS[i % len(WHITE_KEYS)],
            octave_shift + i // len(WHITE_KEYS),
        )
    for i, c in enumerate(black_line):
        i_rel = i % len(WHITE_KEYS)
        if i_rel in (2, 6):
            continue
        if i_rel > 2:
            i_rel -= 1
        assert 0 <= i_rel < 5
        key_mapping[ord(c)] = (BLACK_KEYS[i_rel], octave_shift + i // len(WHITE_KEYS))
key_reverse_mapping = {octave_note: chr(key) for key, octave_note in key_mapping.items()}
max_shift = max(oct_sh for n, oct_sh in key_mapping.values())

# text is the surface displaying the note names and corresponding keyboard key
text = pygame.Surface((width * OCTAVES, 40), pygame.SRCALPHA)


def redraw_note_names():
    text.fill((255, 255, 255, 0))
    for octave in range(LOWEST, LOWEST + OCTAVES):
        offset = width * (octave - LOWEST)
        for n, notename in enumerate(WHITE_KEYS):
            note_offset = offset + n * white_key_width + (white_key_width // 2)
            note_text = f"{notename}{octave}"
            note_glyph = font.render(note_text, 2, (0, 0, 0))
            text.blit(note_glyph, (note_offset - note_glyph.get_width() // 2, 0))
            # key_key = (notename, current_octave - octave, )
            if current_octave <= octave <= current_octave + max_shift:
                key_text = key_reverse_mapping[notename, octave - current_octave]
                if key_text == "\t":
                    key_text = "Tab"
                elif key_text == "\n" or key_text == "\r":
                    key_text = "Ent"
                key_glyph = font.render(key_text, 2, (0, 0, 0))
                text.blit(key_glyph, (note_offset - key_glyph.get_width() // 2, 20))


redraw_note_names()
quit = False

while not quit:

    # Blit the picture of one octave OCTAVES times.

    for x in range(OCTAVES):
        screen.blit(key_graphic, (x * width, 0))

    # Blit the text surface

    screen.blit(text, (0, height - text.get_height()))

    note_ctl.tick()

    # Check for keypresses

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit = True
        elif event.type == pygame.KEYDOWN:
            if event.key in key_mapping:
                note_n, octave_sh = key_mapping[event.key]
                note_ctl.play_note(note_n, current_octave + octave_sh)
            elif event.key == pygame.K_LEFT:
                current_octave -= 1
                redraw_note_names()
            elif event.key == pygame.K_RIGHT:
                current_octave += 1
                redraw_note_names()
            elif event.key == pygame.K_DOWN:
                current_channel -= 1
            elif event.key == pygame.K_UP:
                current_channel += 1
            elif event.key == pygame.K_ESCAPE:
                quit = True
        elif event.type == pygame.KEYUP:
            if event.key in key_mapping:
                note_n, octave_sh = key_mapping[event.key]
                note_ctl.stop_note(note_n, current_octave + octave_sh)

    # Update the screen

    pygame.display.update()

if RECORD_FILE is not None and note_ctl.start_time is not None:
    fluidsynth.midi.sleep(time.time() - note_ctl.start_time)
pygame.quit()

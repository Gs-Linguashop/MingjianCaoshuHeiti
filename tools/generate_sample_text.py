# MenuTitle: Generate Random String from Font
# -*- coding: utf-8 -*-
__doc__ = """
Ask for an input string, then generate a random string of 5× its length,
containing the given characters and random characters from the font.
Skips missing glyphs. Opens result in a new Edit tab.
"""

from GlyphsApp import *
import random
import vanilla

font = Glyphs.font
if not font:
	Message("No Font Open", "Please open a font first.")
	raise SystemExit

class RandomStringGenerator:
	def __init__(self):
		self.w = vanilla.FloatingWindow((300, 100), "Input String")
		self.w.text = vanilla.TextBox((15, 12, 100, 20), "Enter string:")
		self.w.input = vanilla.EditText((110, 10, 170, 24), "")
		self.w.ok = vanilla.Button((110, 45, 80, 24), "OK", callback=self.generate)
		self.w.cancel = vanilla.Button((200, 45, 80, 24), "Cancel", callback=self.cancel)
		self.w.open()

	def generate(self, sender):
		input_str = self.w.input.get().strip()
		self.w.close()
		if not input_str:
			Message("Empty input", "Please enter at least one character.")
			return

		available_chars = []
		for g in font.glyphs:
			if g.export and g.unicode:
				try:
					c = chr(int(g.unicode, 16))
					available_chars.append(c)
				except Exception:
					pass

		if not available_chars:
			Message("No glyphs", "No displayable glyphs found in this font.")
			return

		l = len(input_str)
		target_len = 5 * l
		result_chars = list(input_str)
		while len(result_chars) < target_len:
			result_chars.append(random.choice(available_chars))

		random.shuffle(result_chars)
		random_string = "".join(result_chars)

		# Print and show result
		print("Input:", input_str)
		print("Output:", random_string)
		font.newTab(random_string)

	def cancel(self, sender):
		self.w.close()

RandomStringGenerator()

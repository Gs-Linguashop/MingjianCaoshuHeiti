def parse_str(s, keep_bracket=False):
	"""
	Split a string into list of single-character strings,
	but keep substrings enclosed in [...] together.

	Example:
		"A[Bc]D[e]F" → ["A", "Bc", "D", "e", "F"]
	"""
	result = []
	i = 0
	while i < len(s):
		if s[i] == "[":
			j = s.find("]", i + 1)
			if j == -1:
				# no closing bracket, take the rest
				if keep_bracket: result.append('[' + s[i+1:])
				else: result.append(s[i+1:])
				break
			if keep_bracket: result.append('[' + s[i+1:] + ']')
			else: result.append(s[i+1:j])
			i = j + 1
		else:
			result.append(s[i])
			i += 1
	return result
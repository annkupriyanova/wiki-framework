class Page:
    section_order = {0: 'description', 1: 'part_of_speech', 2: 'synonyms',
                     3: 'similar_words', 4: 'photo', 5: 'audio',
                     6: 'video'}

    def __init__(self, word, attr_dict):
        self.word = word
        self.sections = ['word']
        self.media_info = False
        self.additional_info = False
        for key, val in attr_dict.items():
            if key in ['audio', 'photo', 'video']:
                self.media_info = True
            if key in ['synonyms', 'similar_words']:
                self.additional_info = True
            self.__setattr__(key.lower(), val)
            self.sections.append(key)

    @property
    def text(self):
        text = f'**{self.word}**\n'
        if 'description' in self.sections:
            text += '==Description==\n'
            text += self.description + '\n'




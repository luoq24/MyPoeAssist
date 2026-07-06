from datetime import datetime

from PyQt6.QtWidgets import QLabel, QPlainTextEdit, QAbstractScrollArea



class StatusInfoMultiLine(object):

    def __init__(self, textContainer: QLabel | QPlainTextEdit, max_lines: int=10, show_time: bool=True):
        self._textContainer = textContainer
        self._count_max = max_lines
        self._show_time = show_time
        self._list_status_info: list[str] = []
        self._set_text: callable = None
        
        self.set_funcs()

    def set_funcs(self):
        if isinstance(self._textContainer, QPlainTextEdit):
            self._set_text = self._textContainer.setPlainText
        else:
            container: QLabel = self._textContainer
            self._set_text = container.setText

    def _scroll_to_bottom(self):
        if isinstance(self._textContainer, QAbstractScrollArea):
            self._textContainer.verticalScrollBar().setValue(self._textContainer.verticalScrollBar().maximum())

    def add_desc(self, msg: str):        
        if self._show_time:
            formatted_time = datetime.now().strftime("%H:%M:%S")
            msg = '[{}]{}'.format(formatted_time, msg)

        self._list_status_info.append(msg)

        if len(self._list_status_info) > self._count_max:
            self._list_status_info.pop(0)

        text = '\n'.join(self._list_status_info)
        
        self._set_text(text)

        self._scroll_to_bottom()

"""PySide6 window for wholagged."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, __version__
from .checks import CHECKS, CheckSpec, run_checks
from .models import CheckResult, Side, Status, Verdict
from .report import build_report
from .verdict import decide

STEAMSTAT_URL = "https://steamstat.us/"
ISDOWN_URL = "https://isdown.app/status/dota-2"

BG = "#111317"
CARD = "#1a1d23"
CARD_HI = "#21252c"
BORDER = "#2b3038"
TEXT = "#e9e7e4"
MUTED = "#8d939e"
ACCENT = "#c8402e"
RUNNING = "#58a6ff"

STATUS_COLORS = {
    Status.OK: "#3fb950",
    Status.WARN: "#d29922",
    Status.FAIL: "#f85149",
    Status.SKIP: "#6e7681",
}
STATUS_WORDS = {
    Status.OK: "Կարգին է",
    Status.WARN: "Ուշադրություն",
    Status.FAIL: "Չի աշխատում",
    Status.SKIP: "Բաց թողնվեց",
}
SIDE_STYLE = {
    Side.YOU: ("#f85149", "ՔՈ ԿՈՂՄԻՑ"),
    Side.ISP: ("#d29922", "PROVIDER / ROUTE"),
    Side.VALVE: ("#a371f7", "VALVE-Ի ԿՈՂՄԻՑ"),
    Side.PC: ("#3fb950", "ՑԱՆՑԸ ԿԱՐԳԻՆ Է"),
    Side.UNCLEAR: ("#d29922", "VALVE ԿԱՄ PROVIDER"),
}

STYLE = f"""
QWidget {{ background: {BG}; color: {TEXT}; }}
QScrollArea {{ border: none; }}
QLabel {{ background: transparent; }}
QLabel#title {{ font-size: 21pt; font-weight: 700; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 10.5pt; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#details {{ color: {MUTED}; font-size: 9pt; }}
QLabel#rowTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#headline {{ font-size: 15pt; font-weight: 700; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QPushButton {{
    background: {CARD_HI}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 8px 14px; font-size: 10pt;
}}
QPushButton:hover {{ border-color: #4a515c; }}
QPushButton:disabled {{ color: #5b616b; }}
QPushButton#primary {{
    background: {ACCENT}; border: none; color: white; font-weight: 700;
    font-size: 11pt; padding: 11px 22px;
}}
QPushButton#primary:hover {{ background: #d9503d; }}
QPushButton#primary:disabled {{ background: #5a2a23; color: #c9a8a2; }}
QPushButton#link {{
    background: transparent; border: none; color: {MUTED}; padding: 2px 0;
    font-size: 9pt; text-align: left;
}}
QPushButton#link:hover {{ color: {TEXT}; }}
QProgressBar {{
    background: {CARD}; border: none; border-radius: 3px; max-height: 6px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
"""


def _dot(color: str) -> str:
    return f"background: {color}; border-radius: 6px; min-width: 12px; max-width: 12px; min-height: 12px; max-height: 12px;"


class CheckRow(QFrame):
    def __init__(self, spec: CheckSpec, index: int) -> None:
        super().__init__()
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.dot = QLabel()
        self.dot.setFixedSize(12, 12)
        top.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(f"{index}. {spec.title}")
        self.title.setObjectName("rowTitle")
        self.summary = QLabel(spec.hint)
        self.summary.setObjectName("muted")
        self.summary.setTextFormat(Qt.TextFormat.PlainText)  # shows text from Valve's API: never as HTML
        self.summary.setWordWrap(True)
        text_col.addWidget(self.title)
        text_col.addWidget(self.summary)
        top.addLayout(text_col, 1)

        self.state = QLabel("")
        self.state.setObjectName("muted")
        self.state.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.state)
        outer.addLayout(top)

        self.toggle = QPushButton("Մանրամասներ ▸")
        self.toggle.setObjectName("link")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.clicked.connect(self._toggle_details)
        self.toggle.hide()
        self.details = QLabel()
        self.details.setObjectName("details")
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.hide()
        detail_box = QVBoxLayout()
        detail_box.setContentsMargins(24, 0, 0, 0)
        detail_box.setSpacing(2)
        detail_box.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignLeft)
        detail_box.addWidget(self.details)
        outer.addLayout(detail_box)

        self.spec = spec
        self.set_pending()

    def set_pending(self) -> None:
        self.dot.setStyleSheet(_dot("#3a3f48"))
        self.summary.setText(self.spec.hint)
        self.state.setText("")
        self.state.setStyleSheet("")
        self.toggle.hide()
        self.details.hide()

    def set_running(self) -> None:
        self.dot.setStyleSheet(_dot(RUNNING))
        self.state.setText("Ստուգվում է…")
        self.state.setStyleSheet(f"color: {RUNNING};")

    def set_result(self, res: CheckResult) -> None:
        color = STATUS_COLORS[res.status]
        self.dot.setStyleSheet(_dot(color))
        self.summary.setText(res.summary)
        self.state.setText(STATUS_WORDS[res.status])
        self.state.setStyleSheet(f"color: {color}; font-weight: 600;")
        if res.details:
            self.details.setText("\n".join(res.details))
            self.toggle.setText("Մանրամասներ ▸")
            self.toggle.show()
            # Open the details of problems right away.
            if res.status in (Status.WARN, Status.FAIL):
                self._toggle_details()

    def _toggle_details(self) -> None:
        visible = not self.details.isVisible()
        self.details.setVisible(visible)
        self.toggle.setText("Մանրամասներ ▾" if visible else "Մանրամասներ ▸")


class VerdictCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(8)
        self.chip = QLabel()
        self.chip.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.headline = QLabel()
        self.headline.setObjectName("headline")
        self.headline.setTextFormat(Qt.TextFormat.PlainText)
        self.headline.setWordWrap(True)
        self.explanation = QLabel()
        self.explanation.setTextFormat(Qt.TextFormat.PlainText)
        self.explanation.setWordWrap(True)
        self.advice_title = QLabel("Ինչ անել")
        self.advice_title.setObjectName("rowTitle")
        self.advice = QLabel()
        self.advice.setWordWrap(True)
        self.advice.setTextFormat(Qt.TextFormat.RichText)
        for w in (self.chip, self.headline, self.explanation, self.advice_title, self.advice):
            lay.addWidget(w, 0, Qt.AlignmentFlag.AlignLeft if w is self.chip else Qt.AlignmentFlag(0))
        self.hide()

    def show_verdict(self, verdict: Verdict) -> None:
        color, label = SIDE_STYLE[verdict.side]
        self.setStyleSheet(
            f"QFrame#card {{ background: {CARD}; border: 2px solid {color}; border-radius: 10px; }}"
        )
        self.chip.setText(label)
        self.chip.setStyleSheet(
            f"color: {BG}; background: {color}; border-radius: 4px; padding: 3px 9px;"
            " font-size: 8.5pt; font-weight: 700;"
        )
        self.headline.setText(verdict.headline)
        self.explanation.setText(verdict.explanation)
        items = "".join(f"<li style='margin-bottom:4px'>{_html(a)}</li>" for a in verdict.advice)
        self.advice.setText(f"<ol style='margin-left:-20px'>{items}</ol>")
        self.show()


def _html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class CheckWorker(QThread):
    check_started = Signal(str)
    check_done = Signal(object)
    all_done = Signal(object, object)

    def run(self) -> None:
        results = run_checks(
            on_start=lambda spec: self.check_started.emit(spec.key),
            on_result=self.check_done.emit,
        )
        self.all_done.emit(results, decide(results))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(760, 860)
        self.worker: CheckWorker | None = None
        self.results: dict[str, CheckResult] = {}
        self.verdict: Verdict | None = None

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        subtitle = QLabel("Ստուգում է Dota 2-ի կապը՝ խնդիրը քո internet-ի՞ց է, provider-ի՞ց, թե՞ Valve-ի սերվերներից")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addSpacing(6)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Սկսել ստուգումը")
        self.run_btn.setObjectName("primary")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self.start)
        run_row.addWidget(self.run_btn)
        self.status_lbl = QLabel("Մոտ 10–20 վայրկյան")
        self.status_lbl.setObjectName("muted")
        run_row.addWidget(self.status_lbl, 1)
        lay.addLayout(run_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, len(CHECKS))
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        lay.addWidget(self.progress)

        self.verdict_card = VerdictCard()
        lay.addWidget(self.verdict_card)

        self.rows: dict[str, CheckRow] = {}
        for i, spec in enumerate(CHECKS, 1):
            row = CheckRow(spec, i)
            self.rows[spec.key] = row
            lay.addWidget(row)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.copy_btn = QPushButton("Պատճենել report-ը")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_report)
        steamstat_btn = QPushButton("steamstat.us")
        steamstat_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(STEAMSTAT_URL)))
        isdown_btn = QPushButton("Ուրիշների բողոքները")
        isdown_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ISDOWN_URL)))
        for b in (self.copy_btn, steamstat_btn, isdown_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            footer.addWidget(b)
        footer.addStretch(1)
        version = QLabel(f"v{__version__}")
        version.setObjectName("muted")
        footer.addWidget(version)
        lay.addSpacing(4)
        lay.addLayout(footer)
        lay.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.setCentralWidget(scroll)

    # -- actions ------------------------------------------------------------ #
    def start(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.results = {}
        self.verdict = None
        self.verdict_card.hide()
        self.copy_btn.setEnabled(False)
        for row in self.rows.values():
            row.set_pending()
        self.progress.setValue(0)
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Ստուգվում է…")
        self.status_lbl.setText("")

        self.worker = CheckWorker(self)
        self.worker.check_started.connect(self._on_started)
        self.worker.check_done.connect(self._on_done)
        self.worker.all_done.connect(self._on_all_done)
        self.worker.start()

    def _on_started(self, key: str) -> None:
        self.rows[key].set_running()
        spec = next(s for s in CHECKS if s.key == key)
        self.status_lbl.setText(spec.hint + "…")

    def _on_done(self, res: CheckResult) -> None:
        self.results[res.key] = res
        self.rows[res.key].set_result(res)
        self.progress.setValue(len(self.results))

    def _on_all_done(self, results: dict[str, CheckResult], verdict: Verdict) -> None:
        self.results = results
        self.verdict = verdict
        self.verdict_card.show_verdict(verdict)
        self.copy_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Նորից ստուգել")
        self.status_lbl.setText("Պատրաստ է")

    def copy_report(self) -> None:
        QGuiApplication.clipboard().setText(build_report(self.results, self.verdict))
        self.copy_btn.setText("Պատճենվեց ✓")
        QTimer.singleShot(1600, lambda: self.copy_btn.setText("Պատճենել report-ը"))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            self.hide()
            self.worker.wait()  # every check has a timeout, so this ends soon
        event.accept()


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    return app.exec()

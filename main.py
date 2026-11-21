import os, sqlite3, sys
from pathlib import Path
from datetime import date, datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QPushButton,
 QVBoxLayout,QHBoxLayout,QStackedWidget,QListWidget,QListWidgetItem,QLineEdit,QCheckBox,
 QDialog,QFormLayout,QDateEdit,QDialogButtonBox,QMessageBox)

DATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FocusForge"
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / "focusforge.db"

class Store:
    def __init__(self):
        self.c = sqlite3.connect(DB)
        self.c.row_factory = sqlite3.Row
        self.c.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT,due TEXT,priority TEXT,done INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS habits(id INTEGER PRIMARY KEY,name TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS logs(habit_id INTEGER,day TEXT,done INTEGER,PRIMARY KEY(habit_id,day));
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,started TEXT,seconds INTEGER,kind TEXT);
        """)
        self.c.commit()
    def tasks(self):
        return self.c.execute("SELECT * FROM tasks WHERE due=? ORDER BY done,id DESC",(date.today().isoformat(),)).fetchall()
    def add_task(self,t,d,p):
        self.c.execute("INSERT INTO tasks(title,due,priority) VALUES(?,?,?)",(t,d,p)); self.c.commit()
    def task_done(self,i,v):
        self.c.execute("UPDATE tasks SET done=? WHERE id=?",(int(v),i)); self.c.commit()
    def delete_task(self,i):
        self.c.execute("DELETE FROM tasks WHERE id=?",(i,)); self.c.commit()
    def habits(self):
        return self.c.execute("SELECT * FROM habits ORDER BY name").fetchall()
    def add_habit(self,n):
        self.c.execute("INSERT OR IGNORE INTO habits(name) VALUES(?)",(n,)); self.c.commit()
    def habit_done(self,i):
        r=self.c.execute("SELECT done FROM logs WHERE habit_id=? AND day=?",(i,date.today().isoformat())).fetchone()
        return bool(r["done"]) if r else False
    def set_habit(self,i,v):
        self.c.execute("INSERT INTO logs VALUES(?,?,?) ON CONFLICT(habit_id,day) DO UPDATE SET done=excluded.done",(i,date.today().isoformat(),int(v))); self.c.commit()
    def save_session(self,s,k):
        self.c.execute("INSERT INTO sessions(started,seconds,kind) VALUES(?,?,?)",(datetime.now().isoformat(),s,k)); self.c.commit()
    def focus_minutes(self):
        r=self.c.execute("SELECT COALESCE(SUM(seconds),0) n FROM sessions WHERE date(started)=? AND kind='Focus'",(date.today().isoformat(),)).fetchone()
        return r["n"]//60
    def close(self): self.c.close()

class TaskDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("Add task")
        f=QFormLayout(self); self.title=QLineEdit(); self.title.setPlaceholderText("Task description")
        self.due=QDateEdit(); self.due.setCalendarPopup(True); self.due.setDate(date.today())
        self.priority=QLineEdit("Medium")
        f.addRow("Task",self.title); f.addRow("Due date",self.due); f.addRow("Priority",self.priority)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)
    def values(self):
        p=self.priority.text().title()
        if p not in ("High","Medium","Low"): p="Medium"
        return self.title.text().strip(),self.due.date().toString("yyyy-MM-dd"),p

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.db=Store(); self.setWindowTitle("FocusForge"); self.resize(1100,720)
        self.mode="Focus"; self.duration=1500; self.left=1500
        root=QWidget(); row=QHBoxLayout(root); row.setContentsMargins(0,0,0,0)
        side=QFrame(); side.setFixedWidth(215); side.setObjectName("Side"); sl=QVBoxLayout(side)
        brand=QLabel("FocusForge"); brand.setObjectName("Brand"); sl.addWidget(brand)
        self.stack=QStackedWidget(); self.pages={}; self.nav=[]
        for name,fn in [("Dashboard",self.dashboard),("Tasks",self.tasks_page),("Habits",self.habits_page),("Focus Timer",self.timer_page)]:
            page=fn(); self.pages[name]=page; self.stack.addWidget(page)
            b=QPushButton(name); b.setCheckable(True); b.setObjectName("Nav"); b.clicked.connect(lambda checked=False,n=name:self.go(n)); sl.addWidget(b); self.nav.append(b)
        sl.addStretch(); sl.addWidget(QLabel("OFFLINE • LOCAL DATABASE")); row.addWidget(side); row.addWidget(self.stack,1); self.setCentralWidget(root)
        self.clock=QTimer(self); self.clock.setInterval(1000); self.clock.timeout.connect(self.tick); self.go("Dashboard")
    def shell(self,title,sub=""):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24)
        h=QLabel(title); h.setObjectName("Title"); l.addWidget(h)
        if sub: l.addWidget(QLabel(sub))
        return p,l
    def metric(self,title):
        f=QFrame(); f.setObjectName("Card"); l=QVBoxLayout(f); l.addWidget(QLabel(title.upper())); v=QLabel("0"); v.setObjectName("Metric"); l.addWidget(v); return f,v
    def dashboard(self):
        p,l=self.shell("Dashboard",date.today().strftime("%A, %d %B %Y")); r=QHBoxLayout()
        self.mtasks=self.metric("Tasks completed"); self.mfocus=self.metric("Focus minutes"); self.mhabits=self.metric("Habits complete")
        for f,v in (self.mtasks,self.mfocus,self.mhabits): r.addWidget(f)
        l.addLayout(r); l.addWidget(QLabel("Today's tasks")); self.today=QListWidget(); l.addWidget(self.today,1); return p
    def tasks_page(self):
        p,l=self.shell("Tasks","Add and complete your daily tasks.")
        r=QHBoxLayout(); r.addStretch(); a=QPushButton("+ Add task"); a.setObjectName("Accent"); a.clicked.connect(self.add_task); r.addWidget(a); l.addLayout(r)
        self.tasklist=QListWidget(); self.tasklist.itemChanged.connect(self.change_task); l.addWidget(self.tasklist,1)
        d=QPushButton("Delete selected"); d.clicked.connect(self.delete_task); l.addWidget(d); return p
    def habits_page(self):
        p,l=self.shell("Habits","Track daily habit completion.")
        r=QHBoxLayout(); self.habitname=QLineEdit(); self.habitname.setPlaceholderText("New habit"); a=QPushButton("Add habit"); a.setObjectName("Accent"); a.clicked.connect(self.add_habit); r.addWidget(self.habitname,1); r.addWidget(a); l.addLayout(r)
        self.habitlayout=QVBoxLayout(); l.addLayout(self.habitlayout); l.addStretch(); return p
    def timer_page(self):
        p,l=self.shell("Focus Timer","25-minute focus / 5-minute break.")
        l.addStretch(); self.modelabel=QLabel("FOCUS SESSION"); self.modelabel.setAlignment(Qt.AlignCenter); l.addWidget(self.modelabel)
        self.clocklabel=QLabel("25:00"); self.clocklabel.setAlignment(Qt.AlignCenter); self.clocklabel.setObjectName("Clock"); l.addWidget(self.clocklabel)
        r=QHBoxLayout(); r.setAlignment(Qt.AlignCenter)
        self.start=QPushButton("Start"); self.start.setObjectName("Accent"); self.start.clicked.connect(self.toggle); r.addWidget(self.start)
        z=QPushButton("Reset"); z.clicked.connect(self.reset); r.addWidget(z)
        s=QPushButton("Switch focus/break"); s.clicked.connect(self.switch); r.addWidget(s); l.addLayout(r); l.addStretch(); return p
    def go(self,n):
        self.stack.setCurrentWidget(self.pages[n])
        for b in self.nav: b.setChecked(b.text()==n)
        self.refresh()
    def refresh(self):
        ts=self.db.tasks(); done=sum(t["done"] for t in ts); hs=self.db.habits(); hd=sum(self.db.habit_done(h["id"]) for h in hs)
        self.mtasks[1].setText(f"{done}/{len(ts)}"); self.mfocus[1].setText(str(self.db.focus_minutes())); self.mhabits[1].setText(f"{hd}/{len(hs)}")
        self.today.clear()
        if not ts: self.today.addItem("No tasks due today. Add one from Tasks.")
        for t in ts: self.today.addItem(("✓ " if t["done"] else "○ ")+t["title"]+" • "+t["priority"])
        self.tasklist.blockSignals(True); self.tasklist.clear()
        for t in ts:
            it=QListWidgetItem(f'{t["title"]} • {t["priority"]} • {t["due"]}'); it.setData(Qt.UserRole,t["id"]); it.setFlags(it.flags()|Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked if t["done"] else Qt.Unchecked); self.tasklist.addItem(it)
        self.tasklist.blockSignals(False)
        while self.habitlayout.count():
            x=self.habitlayout.takeAt(0)
            if x.widget(): x.widget().deleteLater()
        for h in hs:
            c=QCheckBox(h["name"]); c.setChecked(self.db.habit_done(h["id"])); c.stateChanged.connect(lambda v,i=h["id"]:self.set_habit(i,v==Qt.Checked)); self.habitlayout.addWidget(c)
    def add_task(self):
        d=TaskDialog(self)
        if d.exec()==QDialog.Accepted:
            t,day,p=d.values()
            if not t: QMessageBox.warning(self,"Task required","Enter a task description."); return
            self.db.add_task(t,day,p); self.refresh()
    def change_task(self,item): self.db.task_done(item.data(Qt.UserRole),item.checkState()==Qt.Checked); self.refresh()
    def delete_task(self):
        it=self.tasklist.currentItem()
        if it is None: QMessageBox.information(self,"Select task","Select a task first."); return
        self.db.delete_task(it.data(Qt.UserRole)); self.refresh()
    def add_habit(self):
        n=self.habitname.text().strip()
        if n: self.db.add_habit(n); self.habitname.clear(); self.refresh()
    def set_habit(self,i,v): self.db.set_habit(i,v); self.refresh()
    def toggle(self):
        if self.clock.isActive(): self.clock.stop(); self.start.setText("Resume")
        else: self.clock.start(); self.start.setText("Pause")
    def reset(self): self.clock.stop(); self.left=self.duration; self.start.setText("Start"); self.update_clock()
    def switch(self):
        self.clock.stop(); self.mode="Break" if self.mode=="Focus" else "Focus"; self.duration=300 if self.mode=="Break" else 1500; self.left=self.duration
        self.modelabel.setText(self.mode.upper()+" SESSION"); self.start.setText("Start"); self.update_clock()
    def tick(self):
        self.left-=1; self.update_clock()
        if self.left<=0:
            self.clock.stop(); self.db.save_session(self.duration,self.mode); self.start.setText("Start")
            QMessageBox.information(self,"Session complete",self.mode+" session completed."); self.refresh()
    def update_clock(self): self.clocklabel.setText(f"{self.left//60:02d}:{self.left%60:02d}")
    def closeEvent(self,event): self.clock.stop(); self.db.close(); event.accept()

def main():
    app=QApplication(sys.argv); app.setApplicationName("FocusForge")
    app.setStyleSheet("""
    QWidget{background:#111315;color:#ECEFF1;font-family:'Segoe UI';font-size:10pt}
    QFrame#Side{background:#181B1E;border-right:1px solid #30353A}
    QLabel#Brand{color:#FF8A32;font-size:21pt;font-weight:800;padding:12px}
    QLabel#Title{font-size:22pt;font-weight:700}
    QLabel#Metric{font-size:24pt;font-weight:700;color:#FF9A4D}
    QLabel#Clock{font-size:58pt;font-weight:800;color:#FF9A4D}
    QFrame#Card{background:#1B1F23;border:1px solid #30353A;border-radius:12px}
    QPushButton{background:#272D32;border:1px solid #3A4147;border-radius:8px;padding:9px 13px}
    QPushButton:hover{border-color:#FF8A32}
    QPushButton#Nav{text-align:left;background:transparent;border:0;padding:12px}
    QPushButton#Nav:checked{background:#39291E;color:#FF9A4D}
    QPushButton#Accent{background:#F07B27;color:#161616;border:0;font-weight:700}
    QLineEdit,QDateEdit,QListWidget{background:#181B1E;border:1px solid #394047;border-radius:7px;padding:8px}
    QListWidget::item{padding:8px;border-bottom:1px solid #292E33}
    """)
    w=Window(); w.show(); return app.exec()

if __name__=="__main__": raise SystemExit(main())

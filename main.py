from ball import Ui_Form
from PySide2.QtCore import Qt,QCoreApplication,QTime,QTimer,SIGNAL
from PySide2.QtWidgets import QWidget,QApplication,QMessageBox,QLCDNumber,QProgressBar
from PySide2.QtGui import QMouseEvent
import json
import time,datetime
import sys
from typing import List
from qt_material import apply_stylesheet


QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
#APP
app=QApplication()


class MainWindow(QWidget):
    """管理悬浮球的窗口"""
    def __init__(self):
        super().__init__()
        # 使用ui文件导入定义界面类
        self.ui = Ui_Form()
        # 初始化界面
        self.ui.setupUi(self)
        # 设置窗口无边框； 设置窗口置顶；
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # 设置窗口背景透明
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置透明度(0~1)   
        self.setWindowOpacity(0.9)
        # 设置鼠标为手状
        self.setCursor(Qt.PointingHandCursor)
    #鼠标按下时，记录鼠标相对窗口的位置
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # event.pos() 鼠标相对窗口的位置
            # event.globalPos() 鼠标在屏幕的绝对位置
            self._startPos = event.pos()
    # 鼠标移动时，移动窗口跟上鼠标；同时限制窗口位置，不能移除主屏幕
    def mouseMoveEvent(self, event: QMouseEvent):
        # event.pos()减去最初相对窗口位置，获得移动距离(x,y)
        self._wmGap = event.pos() - self._startPos
        # 移动窗口，保持鼠标与窗口的相对位置不变
        # 检查是否移除了当前主屏幕
        # 左方界限
        final_pos = self.pos() + self._wmGap
        if self.frameGeometry().topLeft().x() + self._wmGap.x() <= 0:
            final_pos.setX(0)
        # 上方界限
        if self.frameGeometry().topLeft().y() + self._wmGap.y() <= 0:
            final_pos.setY(0)
        # 右方界限

        self.move(final_pos)

window=MainWindow()

class System():
    """系统"""
    def __init__(self) -> None:
        self.load_settings()
        self.load_qss()
        self.bind()
        if self.settings['clock']:#是否需要用时钟
            self.start_clock()#启动时钟
        else:
            window.ui.lcdNumber.setHidden(True)#不显示时钟
        self.create_process_bar()            
        if (not self.settings['clock']) and (not self.bars):
            QMessageBox.critical(window,'错误','既不用时钟也不用进度条')
        self.start_bar()
        
        window.show()
        
    def bind(self) -> None:
        #TODO:绑定右击事件
        pass
    def load_settings(self):
        """加载设置"""
        try:
            with open('./settings.json',encoding='utf-8') as f:
                self.settings=json.load(f)
        except FileNotFoundError:
            QMessageBox.about(window,'错误','没有设置文件。为您自动创建！')
            self.settings={}#TODO:默认设置
            self.save_settings()
            #TODO:打开设置
        self.settings.setdefault('update_frequency',500)#更新频率
    def save_settings(self):
        #TODO:保存设置
        with open('./settings.json','w',encoding='utf-8') as f:
            json.dump(self.settings,f,indent=4)
    def load_qss(self):
        """加载窗口样式"""
        window.setStyleSheet('''
        QProgressBar {
        border-radius: 10;
        border: 2px solid grey;
        color: #FFFFFF;
        background:qlineargradient(spread:pad,x1:0,y1:0,x2:1,y2:0,stop:0 red,stop:1 blue);
        }
        ''')
        window.setStyleSheet(self.settings.get('qss_window',''))
        apply_stylesheet(app,self.settings.get('qt_material','dark_teal.xml').replace('none',''))
    def start_clock(self):
        """启动时钟"""
        window.ui.lcdNumber.setSegmentStyle(QLCDNumber.Flat)
        self.clock_timer = QTimer()
        self.clock_timer.connect(self.clock_timer, SIGNAL('timeout()'), self.update_clock)
        self.clock_timer.start(1000)
        window.ui.lcdNumber.setDigitCount(8)#长度
        window.ui.lcdNumber.setStyleSheet("color: white; background: silver;")
    def update_clock(self):
        """时钟更新"""
        now = time.strftime('%H:%M:%S')
        window.ui.lcdNumber.display(now)
    def create_process_bar(self,name:str=''):
        """根据`self.settings`创建进度条"""
        self.bars:List[QProgressBar]=[]
        if name:#加指定的
            percent=self.get_percent(name)#获取当前值
            self.bars.append(QProgressBar(window.ui.processLayout))#创建进度条
            self.bars[-1].setObjectName(name)#将来可以获取
            self.bars[-1].setValue(percent*100)
            window.ui.processLayout.addWidget(self.bars[-1])
        else:#初始化时使用的，全都加上
            for item in self.settings['processes']:
                #item是每一项，根据每一项创建工作
                percent=self.get_percent(item['name'])#获取当前值
                self.bars.append(QProgressBar(window))#创建进度条
                self.bars[-1].setObjectName(item['name'])#将来可以获取
                if percent == float('inf') or percent == float('-inf'):
                    self.bars[-1].setHidden(True)
                else:
                    self.bars[-1].setValue(percent*100)
                window.ui.processLayout.addWidget(self.bars[-1])
    def start_bar(self):
        """启动更新进度条"""
        self.bar_timer = QTimer()
        self.bar_timer.connect(self.bar_timer, SIGNAL('timeout()'), self.update_bar)
        self.bar_timer.start(100)

    def update_bar(self):
        """挨个更新进度条"""
        for bar in self.bars:
            name=bar.objectName()
            percent=self.get_percent(name)#获取当前值
            if percent == float('-inf') or percent == float('inf'):#隐藏这个条
                bar.setHidden(True)
            else:
                bar.setHidden(False)
                bar.setValue(percent*100)
    def get_percent(self,name:str)->float:
        """找到现在的时间应该是百分之几。
        name:str，在`self.settings`里的名字"""
        item=tuple(filter(lambda x:x['name'] == name,
                self.settings['processes'])
                )[0]
        item.setdefault('ndigits',2)#设置小数位数
        #TODO:自动时间日期格式
        try:#获取今天开始结束时间
            start_time=datetime.datetime.combine(datetime.date.today(),datetime.time.fromisoformat(item['start']))
            end_time=datetime.datetime.combine(datetime.date.today(),datetime.time.fromisoformat(item['end']))
        except ValueError:
            QMessageBox.critical(window,'错误',f'名称为{name}的项，时间格式错误！')
            sys.exit(1)
        now_time=datetime.datetime.now()
        if not start_time < end_time:
            QMessageBox.critical(window,'错误',f'名称为{name}的项开始时间在结束时间之后！')
            #TODO:打开设置
        if now_time < start_time:#未开始
            return float('inf')
        elif end_time < now_time:#已结束
            return float('-inf')
        else:
            delta:datetime.timedelta=end_time-start_time
            percent:float=((datetime.datetime.now()-start_time).total_seconds()/#已经过了的时间
                    delta.total_seconds())#总的时间
            return round(percent,item['ndigits'])

system=System()
app.exec_()
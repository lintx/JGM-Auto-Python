import cv2
import uiautomator2 as u2
import multiprocessing
import time
from datetime import datetime
import os
import logging
import re
import threading
import signal
import sys

class Automator:
    def __init__(self, config: dict, targetPath = "targets"):
        """
        device: 如果是 USB 连接，则为 adb devices 的返回结果；如果是模拟器，则为模拟器的控制 URL 。
        """
        self.targetPath = targetPath
        self._init_logging()
        self._init_points(config.get("points"))
        self._init_targets(config.get("target_level"))
        self._init_device(config.get("device"))

    def _init_logging(self):
        print("正在初始化日志...")
        self.targetCount = 0
        self.date = datetime.now().strftime('%Y-%m-%d')
        logDir = os.path.join(self.targetPath,"log")
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        logPath = os.path.join(logDir,self.date + ".log")
        
        if os.path.exists(logPath):
            pattern = r'第(\d+)次收货'
            p = re.compile(pattern)
            
            f = open(logPath,"r")
            lines = f.readlines()
            f.close
            i = 0
            for line in reversed(lines):
                line = line.strip()     #去掉头尾空白
                match = p.search(line)
                if match:
                    count = match.group(1)
                    if count.isnumeric:
                        self.targetCount = int(count)
                        print("检测到上次退出程序时最后一次记录的收货次数为" + count)
                    break
        
        logging.basicConfig(
            level=logging.INFO,#控制台打印的日志级别
            filename=logPath,
            filemode='a',##模式，有w和a，w就是写模式，每次都会重新写日志，覆盖之前的日志
            #a是追加模式，默认如果不写的话，就是追加模式
            format= '%(asctime)s - %(levelname)s: %(message)s' #日志格式
        )
        
        logging.info("程序开始启动")
        
    def _init_points(self, points: dict):
        """
        根据左下角建筑和右上角建筑来确定全部9个建筑的坐标
        9个建筑物可以视为7行3列，所以中间一列的x坐标即为左边一行和右边一行的x坐标的平均值
        y坐标则先计算出每行的差额，差额为(最下面一行的y坐标-最上面一行的y坐标)/(行数-1)
        然后从上到下，依次累加即为每行的y坐标
        先将右上x-左下x，再/2，等于差额，分别为
        """
        print("正在计算建筑坐标...")
        
        x1 = points.get("left")
        y7 = points.get("bottom")
        x3 = points.get("right")
        y1 = points.get("top")
        
        x2 = (x1 + x3)/2
        
        step = (y7 - y1)/6
        
        y2 = y1 + step
        y3 = y2 + step
        y4 = y3 + step
        y5 = y4 + step
        y6 = y5 + step
        
        self.points = {
            "all":{                 # 所有建筑的坐标点
                1: (x1, y7),
                2: (x2, y6),
                3: (x3, y5),
                4: (x1, y5),
                5: (x2, y4),
                6: (x3, y3),
                7: (x1, y3),
                8: (x2, y2),
                9: (x3, y1)
            },
            "empty": (x2, y1/1),      # 设定空坐标（家国之光等弹窗时，点击空坐标来关闭[这种弹窗都可以点击屏幕空白处关闭]）
            "swipe": [                # 收割金币时滑动屏幕的坐标序列
                (x1, y7, x3, y5),
                (x1, y5, x3, y3),
                (x1, y3, x3, y1)
            ]
        }
        print("建筑坐标计算完成:")
        print("建筑1：" + str(x1) + "," + str(y7))
        print("建筑2：" + str(x2) + "," + str(y6))
        print("建筑3：" + str(x3) + "," + str(y5))
        print("建筑4：" + str(x1) + "," + str(y5))
        print("建筑5：" + str(x2) + "," + str(y4))
        print("建筑6：" + str(x3) + "," + str(y3))
        print("建筑7：" + str(x1) + "," + str(y3))
        print("建筑8：" + str(x2) + "," + str(y2))
        print("建筑9：" + str(x3) + "," + str(y1))

    def _init_device(self, device: dict):
        print("正在连接adb设备...")
        url = device.get("host") + ":" + device.get("port")
        self.d = u2.connect(url)
        self._click_empty()
        screen = self._screen()
        dh, dw = screen.shape[:2]
        self.device_config = {
            "width": dw,
            "height": dh,
            "start_x": int(dw/2),
            "start_y": int(dh/10*7),
            "end_x": dw,
            "end_y": int(dh/10*9)
        }
        print("设备连接完毕，设备屏幕大小：" + str(dw) + "x" + str(dh))
        
    def _init_targets(self, targetLevel):
        print("正在获取小火车货物图像...")
        files = os.listdir(self.targetPath)
        self.targets = []
        for file in files: #遍历文件夹
            if os.path.isdir(file):  #判断是否是文件夹
                continue
                
            arr = file.split("-",2)
            if len(arr) < 3:
                continue
                
            level = 0
            if arr[1].isnumeric:
                level = int(arr[1])
            if level < 1 or level > 3:
                continue
                
            if not arr[0].isnumeric():
                continue
            point = int(arr[0])
            if point < 1 or point > 9:
                continue
                
            if level < targetLevel:
                continue
                
            ls = ""
            if level == 1:
                ls = "蓝色"
            elif level == 2:
                ls = "紫色"
            elif level == 3:
                ls = "橙色"
            
            img = cv2.imread(os.path.join(self.targetPath,file))
            ih, iw = img.shape[:2]
            print("获取到货物图像：" + file + ",建筑品质：" + ls + ",大小：" + str(iw) + "x" + str(ih))
            self.targets.append({
                "img": img,
                "x": int(iw),
                "y": int(ih),
                "point": point
            })
        print("小火车货物图像获取完毕...")
        
    def _click_empty(self):
        self.d.click(*self.points.get("empty"))
        
    def _swipe_money(self):
        """
        滑动屏幕，收割金币。
        """
        for points in self.points.get("swipe"):
            self.d.swipe(*points)
            
    def _screen(self):
        return self.d.screenshot(format="opencv")
        
    def _get_point(self, point):
        return self.points.get("all").get(point)
    
    def start(self):
        self.last = datetime.now()
        self.first = datetime.now()
        self.testTarget = False
        self.taskRunning = False
        self.task = None
        print("脚本开始启动")
        
        self._start()
        self._help()
        while True:
            str = input("> ")
            if str == "start":
                self._start()
            elif str == "stop":
                self._stop()
            elif str == "help":
                self._help()
    
    def _help(self):
        print("输入命令\"stop\"并回车可以暂停脚本")
        print("输入命令\"start\"并回车可以恢复脚本")
        print("输入命令\"help\"并回车可以显示帮助")
    
    def quit(self, signum, frame):
        sys.exit()
        
    def _start(self):
        if self.taskRunning or not self.task is None:
            print("脚本正在运行中，无法重复运行")
            return
        print("正在启动脚本...")
        self.taskRunning = True
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        self.task = threading.Thread(target=self._run)
        self.task.setDaemon(True)
        self.task.start()
        print("脚本启动成功")
        
    def _stop(self):
        print("正在暂停脚本...")
        self.taskRunning = False
    
    def _run(self):
        """
        启动脚本，请确保已进入游戏页面。
        """
        while self.taskRunning:
            """
            简单粗暴的方式，处理 “XX之光” 的荣誉显示。
            当然，也可以使用图像探测的模式。
            先点击一次，然后再检测小火车
            否则如果uiautomator跑到后台了，就会出现无法截图的问题
            导致crash，先点击一次可以把uiautomator激活
            """
            self._click_empty()
            time.sleep(0.1)
            
            t = datetime.now()
            if self.testTarget:
                if (t - self.last).seconds > 600:
                    print("检测到小火车停止发货，最后一次小火车时间：" + str(self.last) + "，总共收货次数" + str(self.targetCount))
                    logging.info("检测到小火车停止发货，最后一次小火车时间：" + str(self.last) + "，总共收货次数" + str(self.targetCount))
                    self.testTarget = False
            self._match_target()


            # 滑动屏幕，收割金币。
            self._swipe_money()
            
            if not self.taskRunning:
                self.task = None
                print("\b\b脚本已暂停\n> ",end="")

    def _match_target(self):
        """
        探测货物，并搬运货物。
        """
        # 获取当前屏幕快照
        config = self.device_config
        start_x = config.get("start_x")
        start_y = config.get("start_y")
        end_x = config.get("end_x")
        end_y = config.get("end_y")
        
        screen = self._screen()
        screen = screen[start_y:end_y, start_x:end_x]
        
        t = datetime.now()
        
        for target in self.targets:
            img = target.get("img")
            x = target.get("x")
            y = target.get("y")
            point = target.get("point")
            position = self._get_point(point)
            if position is None:
                continue
            
            res = cv2.matchTemplate(screen, img, cv2.TM_SQDIFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if min_val > 0.15:
                continue
            if self.date != t.strftime('%Y-%m-%d'):
                self._init_logging()
                print(str(t) + "检测到小火车开始发货")
                logging.info(str(t) + "检测到小火车开始发货")
                self.first = t
                self.testTarget = True
            self.last = datetime.now()
            self.targetCount = self.targetCount + 1
            logging.info("第" + str(self.targetCount) + "次收货，建筑编号：" + str(point))
            
            for i in range(6):
                self.d.swipe(min_loc[0] + start_x + x, min_loc[1] + start_y + y, *position)
                time.sleep(0.1)
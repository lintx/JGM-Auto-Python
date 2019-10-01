from automator import Automator
import sys

if __name__ == '__main__':
    config = {
        "device": {
            "host": "127.0.0.1",        #安卓模拟器adb通讯的ip地址
            "port": "7555"              #安卓模拟器adb通讯的端口，mumu模拟器默认为7555
        },
        "points":{                      #左下建筑和右上建筑的中心的坐标
            "left": 200,                #左下建筑的x坐标
            "bottom": 820,              #左下建筑的y坐标
            "right": 530,               #右上建筑的x坐标
            "top": 310                  #右上建筑的y坐标
        },
		"target_level": 3				#小火车拉货等级，1-3，1表示全部都拉，2表示紫色和橙色，3表示橙色，需要配合文件名
    }

    targetPath = "targets"
    if len(sys.argv) > 1:
        targetPath = sys.argv[1]
    # 连接 adb 。
    instance = Automator(config,targetPath)
    

    # 启动脚本。
    instance.start()

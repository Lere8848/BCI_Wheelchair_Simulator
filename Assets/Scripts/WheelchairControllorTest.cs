using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

// 轮椅控制器脚本
public class WheelchairController : MonoBehaviour
{
    private ROSConnection ros; // ROS连接实例

    public string topicName = "/cmd_vel"; // 订阅的主题名称
    public float linearScale = 1.0f;      // 线速度缩放系数
    public float angularScale = 100.0f;   // 角速度缩放系数

    private float linearVelocity = 0f;    // 当前线速度
    private float angularVelocity = 0f;   // 当前角速度

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // 获取或创建ROS连接实例
        ros.Subscribe<TwistMsg>(topicName, ReceiveVelocityCommand); // 订阅/cmd_vel主题
    }

    // 接收速度指令的回调函数
    void ReceiveVelocityCommand(TwistMsg msg)
    {
        linearVelocity = (float)msg.linear.x * linearScale;      // 设置线速度
        angularVelocity = (float)msg.angular.z * angularScale;   // 设置角速度
    }

    void Update()
    {
        // 根据线速度移动物体
        transform.Translate(Vector3.forward * linearVelocity * Time.deltaTime);
        // 根据角速度旋转物体
        transform.Rotate(Vector3.up, angularVelocity * Time.deltaTime);
    }
}

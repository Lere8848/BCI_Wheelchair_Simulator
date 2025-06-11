using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using UnityEngine;

// 该脚本用于接收 ROS 的 /cmd_vel 主题消息
// 并将其转换为轮椅轮子控制器的线速度和角速度 用于视觉效果（后续可拓展
public class WheelCmdVelSubscriber : MonoBehaviour
{
    public WheelController controller;

    void Start()
    {
        // 后期如果不用 /cmd_vel 主题，记得修改这里的订阅主题和消息格式
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>(
            "/cmd_vel",
            msg =>
            {
                float linear = (float)msg.linear.x;
                float angular = (float)msg.angular.z;
                controller.UpdateCmdVel(linear, angular);
            });
    }
}

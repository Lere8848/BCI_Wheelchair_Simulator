using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;

public class WheelchairController : MonoBehaviour
{
    private ROSConnection ros;  // ROS连接实例
    public string topicName = "/cmd_vel"; // 订阅的主题名称

    public float linearScale = 1.0f;      // 线速度缩放系数
    public float angularScale = 100.0f;   // 角速度缩放系数（角度/秒）

    private float linearVelocity = 0f;    // 当前线速度
    private float angularVelocity = 0f;   // 当前角速度

    private Rigidbody rb;                 // 刚体组件

    void Start()
    {
        rb = GetComponent<Rigidbody>();
        if (rb == null)
        {
            Debug.LogError("Rigidbody component missing from this GameObject.");
            return;
        }

        ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<TwistMsg>(topicName, ReceiveVelocityCommand);

        Debug.Log("[Wheelchair] ROS connection established. Subscribed to: " + topicName);
    }

    // 回调函数：接收 /cmd_vel 的 Twist 消息
    void ReceiveVelocityCommand(TwistMsg msg)
    {
        linearVelocity = (float)msg.linear.x * linearScale;
        angularVelocity = (float)msg.angular.z * angularScale;

        Debug.Log($"[Wheelchair] Received Twist: linear={linearVelocity:F2}, angular={angularVelocity:F2}");
    }

    void FixedUpdate()
    {
        if (rb == null)
            return;

        // 计算前进方向上的位移
        Vector3 move = transform.forward * linearVelocity * Time.fixedDeltaTime;
        rb.MovePosition(rb.position + move);

        // 计算绕Y轴的旋转
        Quaternion turn = Quaternion.Euler(0f, angularVelocity * Time.fixedDeltaTime, 0f);
        rb.MoveRotation(rb.rotation * turn);
    }
}

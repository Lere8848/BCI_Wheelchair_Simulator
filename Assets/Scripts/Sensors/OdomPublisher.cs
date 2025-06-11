using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;
using RosMessageTypes.Geometry;
using Simulator.SimUtils;

public class OdomPublisher : MonoBehaviour
{
    [Header("Odometry Parameters")]
    public string topicName = "/odom"; // 发布的话题名称
    public GameObject trackedObject;   // 需要跟踪的物体
    public string frameId = "odom";    // 坐标系ID
    public string childFrameId = "base_link"; // 子坐标系ID
    public float publishHz = 10.0f;    // 发布频率（Hz）

    [Header("Noise Control")]
    public bool enableNoise = false;
    public float linearNoiseStdDev = 0.02f;   // m/s
    public float angularNoiseStdDev = 0.05f;  // rad/s

    private Vector3 lastPosition;      // 上一帧的位置
    private Quaternion lastRotation;   // 上一帧的旋转
    private Vector3 linearVelocity;    // 线速度
    private Vector3 angularVelocity;   // 角速度
    private float timer = 0f;          // 计时器

    private ROSConnection ros;         // ROS连接实例

    void Start()
    {
        if (trackedObject == null)
            trackedObject = this.gameObject; // 如果未指定跟踪对象，则默认自身

        lastPosition = trackedObject.transform.position; // 初始化位置
        lastRotation = trackedObject.transform.rotation; // 初始化旋转

        ros = ROSConnection.GetOrCreateInstance(); // 获取或创建ROS连接
        ros.RegisterPublisher<OdometryMsg>(topicName); // 注册话题发布者
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= 1.0f / publishHz) // 达到发布频率时执行
        {
            timer = 0f;

            Vector3 currentPosition = trackedObject.transform.position; // 当前帧位置
            Quaternion currentRotation = trackedObject.transform.rotation; // 当前帧旋转

            linearVelocity = (currentPosition - lastPosition) / Time.deltaTime; // 计算线速度
            angularVelocity = SimUtils.CalculateAngularVelocity(lastRotation, currentRotation, Time.deltaTime); // 计算角速度

            // 添加噪声
            if (enableNoise)
            {
                linearVelocity += new Vector3(
                    SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                    0f,
                    SimUtils.GenerateGaussianNoise() * linearNoiseStdDev
                );

                angularVelocity += new Vector3(
                    0f,
                    0f,
                    SimUtils.GenerateGaussianNoise() * angularNoiseStdDev
                );
            }

            PublishOdom(currentPosition, currentRotation, linearVelocity, angularVelocity); // 发布里程计消息

            lastPosition = currentPosition; // 更新上一帧位置
            lastRotation = currentRotation; // 更新上一帧旋转
        }
    }

    // 发布里程计消息
    void PublishOdom(Vector3 pos, Quaternion rot, Vector3 linVel, Vector3 angVel)
    {
        OdometryMsg msg = new OdometryMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = frameId,
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg()
            },
            child_frame_id = childFrameId,
            pose = new PoseWithCovarianceMsg
            {
                pose = new PoseMsg
                {
                    position = new PointMsg(pos.x, pos.y, pos.z),
                    orientation = new QuaternionMsg(rot.x, rot.y, rot.z, rot.w)
                }
            },
            twist = new TwistWithCovarianceMsg
            {
                twist = new TwistMsg
                {
                    linear = new Vector3Msg(linVel.x, linVel.y, linVel.z),
                    angular = new Vector3Msg(angVel.x, angVel.y, angVel.z)
                }
            }
        };

        ros.Publish(topicName, msg); // 发布消息到ROS
    }
}

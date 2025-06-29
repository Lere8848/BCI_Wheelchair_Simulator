using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using RosMessageTypes.Geometry;
using Simulator.SimUtils;

public class IMUPublisher : MonoBehaviour
{
    [Header("IMU Sensor Parameters")]
    public string topicName = "/imu/data"; // 发布的ROS话题名
    public Rigidbody trackedRigidbody;     // 被追踪的刚体
    public float publishHz = 20.0f;        // 发布频率（Hz）

    [Header("Noise Control")]
    public bool enableNoise = false;       // 是否启用噪声
    public float linearNoiseStdDev = 0.1f;   // 线性加速度噪声标准差（m/s²）
    public float angularNoiseStdDev = 0.01f; // 角速度噪声标准差（rad/s）

    private ROSConnection ros; // ROS连接实例
    private float timer;       // 计时器

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // 获取或创建ROS连接实例
        ros.RegisterPublisher<ImuMsg>(topicName);  // 注册IMU消息发布者

        if (trackedRigidbody == null)
            trackedRigidbody = GetComponent<Rigidbody>(); // 获取刚体组件
    }

    void Update()
    {
        timer += Time.deltaTime; // 累加时间
        if (timer >= 1.0f / publishHz) // 达到发布周期
        {
            timer = 0f;
            PublishIMU(); // 发布IMU数据
        }
    }

    // 发布IMU数据到ROS
    void PublishIMU()
    {
        // 计算线性加速度和角速度
        Vector3 linAcc = trackedRigidbody.linearVelocity / Time.fixedDeltaTime;
        Vector3 angVel = trackedRigidbody.angularVelocity;

        // 如果启用噪声，添加高斯噪声
        if (enableNoise)
        {
            linAcc += new Vector3(
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * linearNoiseStdDev
            );

            angVel += new Vector3(
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev,
                SimUtils.GenerateGaussianNoise() * angularNoiseStdDev
            );
        }

        // 构造IMU消息
        ImuMsg msg = new ImuMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "imu_link", // 坐标系ID
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // 时间戳
            },
            orientation = new QuaternionMsg(),  // 如果需要姿态估计，可以补充
            angular_velocity = new Vector3Msg(angVel.x, angVel.y, angVel.z), // 角速度
            linear_acceleration = new Vector3Msg(linAcc.x, linAcc.y, linAcc.z), // 线性加速度
            orientation_covariance = new double[9], // 姿态协方差
            angular_velocity_covariance = new double[9], // 角速度协方差
            linear_acceleration_covariance = new double[9] // 线性加速度协方差
        };

        ros.Publish(topicName, msg); // 发布消息到ROS
    }
}


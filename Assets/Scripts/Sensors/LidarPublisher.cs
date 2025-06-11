using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using System.Collections.Generic;
using Simulator.SimUtils;
using UnityEngine.Diagnostics;

public class LidarPublisher : MonoBehaviour
{
    [Header("Lidar Parameters")]
    public string topicName = "/scan"; // 发布的话题名称
    public int rays = 100; // 激光束数量
    public float maxDistance = 10f; // 最大测量距离
    public float fov = 180f; // 视场角
    public float publishHz = 5f; // 发布频率

    [Header("Noise Control")]
    public bool enableNoise = false; // 是否启用噪声
    public float noiseStdDev = 0.05f; // 噪声标准差

    private ROSConnection ros; // ROS连接实例
    private float timer; // 计时器

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // 获取或创建ROS连接实例
        ros.RegisterPublisher<LaserScanMsg>(topicName); // 注册LaserScan消息发布者
    }

    void Update()
    {
        timer += Time.deltaTime; // 更新时间
        if (timer > 1f / publishHz) // 达到发布周期
        {
            timer = 0f;
            PublishScan(); // 发布激光扫描数据
        }
    }

    // 发布激光扫描数据
    void PublishScan()
    {
        float angleStart = -fov / 2f; // 起始角度
        float angleIncrement = fov / (rays - 1); // 每束激光的角度增量
        List<float> ranges = new List<float>(); // 存储每束激光的距离

        for (int i = 0; i < rays; i++)
        {
            float angle = angleStart + i * angleIncrement; // 当前激光束的角度
            Vector3 direction = Quaternion.Euler(0, angle, 0) * transform.forward; // 计算方向向量
            Ray ray = new Ray(transform.position, direction); // 创建射线

            float distance = maxDistance; // 默认距离为最大距离
            if (Physics.Raycast(ray, out RaycastHit hit, maxDistance))
                distance = hit.distance; // 如果射线击中物体，记录距离

            // 添加高斯噪声
            if (enableNoise)
            {
                float noise = SimUtils.GenerateGaussianNoise() * noiseStdDev;
                distance = Mathf.Clamp(distance + noise, 0.05f, maxDistance); // 限制距离范围
            }

            ranges.Add(distance); // 添加到距离列表

            // 可视化射线
            Debug.DrawRay(transform.position, direction * distance, Color.red, 0.1f);
        }

        // 构造LaserScan消息
        LaserScanMsg scan = new LaserScanMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "lidar", // 坐标系ID
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // 时间戳
            },
            angle_min = Mathf.Deg2Rad * angleStart, // 最小角度（弧度）
            angle_max = Mathf.Deg2Rad * (angleStart + angleIncrement * (rays - 1)), // 最大角度（弧度）
            angle_increment = Mathf.Deg2Rad * angleIncrement, // 角度增量（弧度）
            time_increment = 0.0f, // 每束激光的时间增量
            scan_time = 1.0f / publishHz, // 扫描时间
            range_min = 0.05f, // 最小测量距离
            range_max = maxDistance, // 最大测量距离
            ranges = ranges.ToArray(), // 距离数组
            intensities = new float[rays] // 强度数组（未使用）
        };

        ros.Publish(topicName, scan); // 发布消息
    }
}

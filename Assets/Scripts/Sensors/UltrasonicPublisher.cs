using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using Simulator.SimUtils;

public class UltrasonicPublisher : MonoBehaviour
{
    [Header("Ultrasonic Sensor Parameters")]
    [Tooltip("May use the /ultrasonic_<id> naming format, e.g., /ultrasonic_front")]
    public string topicName; // ROS话题名称
    public float maxRange = 3.0f; // 最大测量距离
    public float minRange = 0.05f; // 最小测量距离
    public float publishHz = 10.0f; // 发布频率（Hz）

    [Header("Noise Control")]
    public bool enableNoise = false; // 是否启用噪声
    public float noiseStdDev = 0.01f; // 噪声标准差

    private ROSConnection ros; // ROS连接实例
    private float timer = 0f; // 计时器

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // 获取或创建ROS连接实例
        ros.RegisterPublisher<RangeMsg>(topicName); // 注册话题发布者
    }

    void Update()
    {
        timer += Time.deltaTime; // 更新时间
        if (timer >= 1f / publishHz) // 到达发布周期
        {
            timer = 0f;
            PublishUltrasonic(); // 发布超声波数据
        }

        // Debug.DrawRay(transform.position, transform.forward * maxRange, Color.yellow);
    }

    // 发布超声波测距消息
    void PublishUltrasonic()
    {
        float distance = maxRange; // 默认距离为最大值
        Ray ray = new Ray(transform.position, transform.forward); // 从传感器位置向前发射射线

        if (Physics.Raycast(ray, out RaycastHit hit, maxRange)) // 检测是否有物体被射线击中
        {
            distance = hit.distance; // 获取碰撞点距离
        }

        if (enableNoise) // 如果启用噪声
        {
            float noise = SimUtils.GenerateGaussianNoise() * noiseStdDev; // 生成高斯噪声
            distance = Mathf.Clamp(distance + noise, minRange, maxRange); // 限制距离在有效范围内
        }

        // 构造Range消息
        RangeMsg msg = new RangeMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = this.gameObject.name, // 帧ID为当前物体名
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // 时间戳
            },
            radiation_type = RangeMsg.ULTRASOUND, // 辐射类型为超声波
            field_of_view = 0.2f, // 视场角（可选，模拟窄束角）
            min_range = minRange, // 最小测量距离
            max_range = maxRange, // 最大测量距离
            range = distance // 实际测量距离
        };
        Debug.DrawRay(transform.position, transform.forward * distance, Color.cyan, 0.1f); // 在场景中绘制射线
        // Debug.Log($"[ULTRASONIC] position: {transform.position}, direction: {transform.forward}");

        ros.Publish(topicName, msg); // 发布消息到ROS
    }
}

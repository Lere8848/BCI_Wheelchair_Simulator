using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using System.Collections.Generic;
using Simulator.Utils;
using UnityEngine.Diagnostics;

public class LidarPublisher : MonoBehaviour
{
    [Header("Lidar Parameters")]
    public string topicName = "/scan";
    public int rays = 100;
    public float maxDistance = 10f;
    public float fov = 180f;
    public float publishHz = 5f;

    [Header("Noise Control")]
    public bool enableNoise = false;
    public float noiseStdDev = 0.05f;

    private ROSConnection ros;
    private float timer;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<LaserScanMsg>(topicName);
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer > 1f / publishHz)
        {
            timer = 0f;
            PublishScan();
        }
    }

    void PublishScan()
    {
        float angleStart = -fov / 2f;
        float angleIncrement = fov / (rays - 1);
        List<float> ranges = new List<float>();

        for (int i = 0; i < rays; i++)
        {
            float angle = angleStart + i * angleIncrement;
            Vector3 direction = Quaternion.Euler(0, angle, 0) * transform.forward;
            Ray ray = new Ray(transform.position, direction);

            float distance = maxDistance;
            if (Physics.Raycast(ray, out RaycastHit hit, maxDistance))
                distance = hit.distance;

            // 添加高斯噪声
            if (enableNoise)
            {
                float noise = NoiseUtils.GenerateGaussianNoise() * noiseStdDev;
                distance = Mathf.Clamp(distance + noise, 0.05f, maxDistance);
            }

            ranges.Add(distance);

            // 可视化射线
            Debug.DrawRay(transform.position, direction * distance, Color.red, 0.1f);
        }

        LaserScanMsg scan = new LaserScanMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "lidar",
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg()
            },
            angle_min = Mathf.Deg2Rad * angleStart,
            angle_max = Mathf.Deg2Rad * (angleStart + angleIncrement * (rays - 1)),
            angle_increment = Mathf.Deg2Rad * angleIncrement,
            time_increment = 0.0f,
            scan_time = 1.0f / publishHz,
            range_min = 0.05f,
            range_max = maxDistance,
            ranges = ranges.ToArray(),
            intensities = new float[rays]
        };

        ros.Publish(topicName, scan);
    }
}

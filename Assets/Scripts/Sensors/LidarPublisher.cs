using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using System.Collections.Generic;
using Simulator.SimUtils;
using UnityEngine.Diagnostics;

public class LidarPublisher : MonoBehaviour
{
    [Header("Lidar Parameters")]
    public string topicName = "/scan"; // Topic name to publish
    public int rays = 100; // Number of laser rays
    public float maxDistance = 10f; // Maximum measurement distance
    public float fov = 180f; // Field of view
    public float publishHz = 5f; // Publish frequency

    [Header("Noise Control")]
    public bool enableNoise = false; // Whether to enable noise
    public float noiseStdDev = 0.05f; // Noise standard deviation

    private ROSConnection ros; // ROS connection instance
    private float timer; // Timer

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance(); // Get or create ROS connection instance
        ros.RegisterPublisher<LaserScanMsg>(topicName); // Register LaserScan message publisher
    }

    void Update()
    {
        timer += Time.deltaTime; // Update time
        if (timer > 1f / publishHz) // Reached publish cycle
        {
            timer = 0f;
            PublishScan(); // Publish laser scan data
        }
    }

    // Publish laser scan data
    void PublishScan()
    {
        float angleStart = -fov / 2f; // Start angle
        float angleIncrement = fov / (rays - 1); // Angle increment for each laser ray
        List<float> ranges = new List<float>(); // Store distance for each laser ray

        for (int i = 0; i < rays; i++)
        {
            float angle = angleStart + i * angleIncrement; // Current laser ray angle
            Vector3 direction = Quaternion.Euler(0, angle, 0) * transform.forward; // Calculate direction vector
            Ray ray = new Ray(transform.position, direction); // Create ray

            float distance = maxDistance; // Default distance is maximum distance
            if (Physics.Raycast(ray, out RaycastHit hit, maxDistance))
                distance = hit.distance; // If ray hits object, record distance

            // Add Gaussian noise
            if (enableNoise)
            {
                float noise = SimUtils.GenerateGaussianNoise() * noiseStdDev;
                distance = Mathf.Clamp(distance + noise, 0.05f, maxDistance); // Limit distance range
            }

            ranges.Add(distance); // Add to distance list

            // Visualize ray
            Debug.DrawRay(transform.position, direction * distance, Color.red, 0.1f);
        }

        // Construct LaserScan message
        LaserScanMsg scan = new LaserScanMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "lidar", // Coordinate frame ID
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg() // Timestamp
            },
            angle_min = Mathf.Deg2Rad * angleStart, // Minimum angle (radians)
            angle_max = Mathf.Deg2Rad * (angleStart + angleIncrement * (rays - 1)), // Maximum angle (radians)
            angle_increment = Mathf.Deg2Rad * angleIncrement, // Angle increment (radians)
            time_increment = 0.0f, // Time increment for each laser ray
            scan_time = 1.0f / publishHz, // Scan time
            range_min = 0.05f, // Minimum measurement distance
            range_max = maxDistance, // Maximum measurement distance
            ranges = ranges.ToArray(), // Distance array
            intensities = new float[rays] // Intensity array (unused)
        };

        ros.Publish(topicName, scan); // Publish message
    }
}

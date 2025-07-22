using UnityEngine;
using System.Collections.Generic;
using System.IO;

[System.Serializable]
public class TrajectoryPoint
{
    public float time;
    public Vector3 position;
    public Quaternion rotation;
}

public class WheelchairTrajLogger : MonoBehaviour
{
    public float logInterval = 0.2f; // 每隔多少秒记录一次
    public string outputFile = "trajectory.json";

    private List<TrajectoryPoint> trajectory = new List<TrajectoryPoint>();
    private float timer = 0f;

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= logInterval)
        {
            LogCurrentState();
            timer = 0f;
        }
    }

    void LogCurrentState()
    {
        TrajectoryPoint point = new TrajectoryPoint
        {
            time = Time.time,
            position = transform.position,
            rotation = transform.rotation
        };
        trajectory.Add(point);
    }

    public void ExportTrajectory()
    {
        // Get current timestamp in specified format
        string timestamp = System.DateTime.Now.ToString("yyyyMMdd_HHmmss");
        
        // Extract file extension and base name
        string extension = Path.GetExtension(outputFile);
        string baseName = Path.GetFileNameWithoutExtension(outputFile);
        
        // Create new filename with timestamp
        string timestampedFileName = $"{baseName}_{timestamp}{extension}";
        
        // Create Logs directory if it doesn't exist
        string logsDirectory = Path.Combine(Application.dataPath, "Logs");
        if (!Directory.Exists(logsDirectory))
        {
            Directory.CreateDirectory(logsDirectory);
        }
        
        string json = JsonUtility.ToJson(new Wrapper { points = trajectory.ToArray() }, true);
        string path = Path.Combine(logsDirectory, timestampedFileName);
        File.WriteAllText(path, json);
        Debug.Log("[TrajectoryLogger] Exported to: " + path);
    }

    [System.Serializable]
    private class Wrapper
    {
        public TrajectoryPoint[] points;
    }

    public void Export()
    {
        ExportTrajectory(); // 调用内部已有函数 绑定给botton
    }
}

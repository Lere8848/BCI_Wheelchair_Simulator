using UnityEngine;
using System.Collections.Generic;
using System.IO;

[System.Serializable]
public class ObstacleData
{
    public string name;
    public Vector3 position;
    public Vector3 size;
    public Quaternion rotation;
}

[System.Serializable]
public class ObstacleWrapper
{
    public List<ObstacleData> obstacles;
}

public class ObstacleLogger : MonoBehaviour
{
    public string outputFile = "Assets/Logs/obstacles.json";
    public string obstacleTag = "ob";

    void Start()  // 运行场景时自动导出
    {
        ExportObstacles();
    }

    void ExportObstacles()
    {
        GameObject[] obs = GameObject.FindGameObjectsWithTag(obstacleTag);
        List<ObstacleData> dataList = new List<ObstacleData>();

        foreach (GameObject ob in obs)
        {
            BoxCollider box = ob.GetComponent<BoxCollider>();
            if (box == null) continue;

            ObstacleData data = new ObstacleData
            {
                name = ob.name,
                position = ob.transform.position,
                size = Vector3.Scale(box.size, ob.transform.lossyScale),
                rotation = ob.transform.rotation
            };
            dataList.Add(data);
        }

        ObstacleWrapper wrapper = new ObstacleWrapper { obstacles = dataList };
        string json = JsonUtility.ToJson(wrapper, true);
        File.WriteAllText(outputFile, json);
        Debug.Log("[ObstacleExporter] Auto-exported to: " + outputFile);
    }
}

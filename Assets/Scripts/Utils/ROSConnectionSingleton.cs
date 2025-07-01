using UnityEngine;
using Unity.Robotics.ROSTCPConnector;

// 确保 ROSConnection 在多个场景中只有一个实例
public class ROSConnectionSingleton : MonoBehaviour
{
    void Awake()
    {
        // 保证只有一个 ROSConnection 存在
        if (FindObjectsByType<ROSConnection>(FindObjectsSortMode.None).Length > 1)
        {
            Destroy(gameObject);
            return;
        }

        DontDestroyOnLoad(gameObject);
    }
}

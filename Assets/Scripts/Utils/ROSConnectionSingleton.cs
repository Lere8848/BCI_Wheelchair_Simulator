using UnityEngine;
using Unity.Robotics.ROSTCPConnector;

// Ensure ROSConnection has only one instance across multiple scenes
public class ROSConnectionSingleton : MonoBehaviour
{
    void Awake()
    {
        // Ensure only one ROSConnection exists
        if (FindObjectsByType<ROSConnection>(FindObjectsSortMode.None).Length > 1)
        {
            Destroy(gameObject);
            return;
        }

        DontDestroyOnLoad(gameObject);
    }
}

using UnityEngine;
using TMPro;
using Simulator.LoggingModules;

public class CollisionDisplayPanel : MonoBehaviour
{
    public TextMeshProUGUI collisionCountText;
    public CollisionLogger logger;

    void Update()
    {
        if (logger != null)
        {
            collisionCountText.text = logger.GetCollisionCount().ToString();
        }
    }
}

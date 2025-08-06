using UnityEngine;
using TMPro;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;

public class IntentDisplay : MonoBehaviour
{
    public TMP_Text intentText; // 绑定到 UI Text 组件
    private string[] directionNames = { "Left", "Forward", "Right" };

    void Start()
    {
        // 订阅 /user_cmd
        ROSConnection.GetOrCreateInstance().Subscribe<Int8Msg>("/user_cmd", OnUserCmdReceived);
    }

    void OnUserCmdReceived(Int8Msg msg)
    {
        int dir = msg.data;
        if (dir >= 0 && dir < directionNames.Length)
        {
            intentText.text = $"WheelChair Intent: {directionNames[dir]}";
        }
        else
        {
            intentText.text = "WheelChair Intent: Unknown";
        }
    }
}

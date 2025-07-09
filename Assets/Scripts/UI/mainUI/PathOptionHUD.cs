using UnityEngine;
using UnityEngine.UI;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using RosMessageTypes.Geometry;

public class PathOptionHUD : MonoBehaviour
{
    [Header("UI References")]
    public GameObject arrowPanel;
    public Image leftArrow;
    public Image forwardArrow;
    public Image rightArrow;

    private int[] currentOptions = new int[3] { 1, 1, 1 };
    private float linearThreshold = 0.05f;
    private float angularThreshold = 0.05f;
    private bool isStopped = false;

    void Start()
    {
        ROSConnection.GetOrCreateInstance().Subscribe<Int8MultiArrayMsg>("/path_options", PathOptionsCallback);
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>("/cmd_vel", CmdVelCallback);

        if (arrowPanel != null)
            arrowPanel.SetActive(false);  // 默认隐藏
    }

    void CmdVelCallback(TwistMsg msg)
    {
        // 判断是否几乎为静止（线速度和角速度都非常小）
        isStopped = Mathf.Abs((float)msg.linear.x) < linearThreshold &&
                    Mathf.Abs((float)msg.angular.z) < angularThreshold;

        UpdatePanelState();
    }

    void PathOptionsCallback(Int8MultiArrayMsg msg)
    {
        if (msg.data.Length < 3) return;
        // Convert sbyte[] to int[] explicitly
        currentOptions[0] = msg.data[0];
        currentOptions[1] = msg.data[1];
        currentOptions[2] = msg.data[2];

        SetArrowColor(leftArrow, currentOptions[0]);
        SetArrowColor(forwardArrow, currentOptions[1]);
        SetArrowColor(rightArrow, currentOptions[2]);

        UpdatePanelState();
    }

    void UpdatePanelState()
    {
        int openCount = currentOptions[0] + currentOptions[1] + currentOptions[2];

        if (arrowPanel == null) return;

        // 判断是否显示整个面板
        // 如果是当“需要用户输入的时候”即（3s内无用户输入，出现障碍，出现岔路）的时候才会出现
        // 即：/cmd_vel 速度为 0  【这是ros2端的一个设置 当碰到障碍或岔路的时候就停下来】
        // 且 /path_options 中可通方向数 ≥2
        // 这样似乎存在一个问题：如果在一个只能右转的拐角处，/cmd_vel 速度为 0，但 /path_options 中可通方向数为1，那么面板仍然会显示
        // if (isStopped && openCount >= 2)

        if (isStopped)
            arrowPanel.SetActive(true);
        else
            arrowPanel.SetActive(false);
    }

    void SetArrowColor(Image arrow, int status)
    {
        if (arrow == null) return;
        arrow.color = (status == 1) ? Color.green : Color.gray;
    }
}

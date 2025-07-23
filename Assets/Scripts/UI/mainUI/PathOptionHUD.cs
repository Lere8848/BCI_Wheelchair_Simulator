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

    // 状态标志
    private bool isStopped = false; // 轮椅是否停止
    private bool userHasInput = false; // 用户是否有输入
    private float lastInputTime = -999f;
    private float inputTimeout = 3f;

    private bool dangerStop = false;

    void Start()
    {
        ROSConnection.GetOrCreateInstance().Subscribe<Int8MultiArrayMsg>("/path_options", PathOptionsCallback);
        ROSConnection.GetOrCreateInstance().Subscribe<TwistMsg>("/cmd_vel", CmdVelCallback);
        ROSConnection.GetOrCreateInstance().Subscribe<Int8Msg>("/user_cmd", UserCmdCallback);
        ROSConnection.GetOrCreateInstance().Subscribe<BoolMsg>("/danger_stop", DangerStopCallback);

        if (arrowPanel != null)
            arrowPanel.SetActive(false);
    }

    void Update()
    {
        // 检查是否超时
        if (Time.time - lastInputTime > inputTimeout)
            userHasInput = false;

        // 若轮椅仍在运动，但用户3秒无输入，说明local path独自运行 → 显示面板
        if (!isStopped && !userHasInput)
        {
            arrowPanel.SetActive(true);
        }
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

        currentOptions[0] = msg.data[0];
        currentOptions[1] = msg.data[1];
        currentOptions[2] = msg.data[2];

        SetArrowColor(leftArrow, currentOptions[0]);
        SetArrowColor(forwardArrow, currentOptions[1]);
        SetArrowColor(rightArrow, currentOptions[2]);

        UpdatePanelState();
    }

    void UserCmdCallback(Int8Msg msg)
    {
        userHasInput = true;
        lastInputTime = Time.time;
    }

    void DangerStopCallback(BoolMsg msg)
    {
        dangerStop = msg.data;
        UpdatePanelState();
    }

    void UpdatePanelState()
    {
        int openCount = currentOptions[0] + currentOptions[1] + currentOptions[2];

        // if (arrowPanel == null) return;

        bool showPanel = false;

        if (dangerStop)
        {
            showPanel = true; // 危险停止时总是显示面板 (即便没有选项或一个选项)
        }
        else if (isStopped)
        {
            if (openCount >= 2)
                showPanel = true; // 停止时如果有两个或更多选项打开，显示面板
            else if (openCount == 1 && !userHasInput) 
                showPanel = true; // 停止时如果只有一个选项打开且没有用户输入，显示面板
        } // 否则不会唐突显示ui

        arrowPanel.SetActive(showPanel);
    }

    void SetArrowColor(Image arrow, int status)
    {
        if (arrow == null) return;
        arrow.color = (status == 1) ? Color.green : Color.gray;
    }
}

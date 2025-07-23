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
    
    // 方向输入与路径冲突相关
    private int userDirection = -1; // -1: 无输入, 0: 左, 1: 前, 2: 右
    private bool isBlinking = false; // 是否正在闪烁
    private float blinkTimer = 0f;
    private float blinkInterval = 0.5f; // 闪烁间隔
    private Color blinkColor = Color.red; // 闪烁颜色

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
        {
            userHasInput = false;
            // 超时后停止闪烁
            if (isBlinking)
            {
                isBlinking = false;
                ResetArrowColors(); // 恢复正常颜色
            }
        }

        // 若轮椅仍在运动，但用户3秒无输入，说明local path独自运行 → 显示面板
        if (!isStopped && !userHasInput)
        {
            arrowPanel.SetActive(true);
        }
        
        // 处理箭头闪烁
        if (isBlinking && userDirection >= 0 && userDirection <= 2)
        {
            blinkTimer += Time.deltaTime;
            
            // 控制闪烁频率
            if (blinkTimer % blinkInterval < blinkInterval * 0.5f)
            {
                // 显示红色
                BlinkDirectionArrow(userDirection, true);
            }
            else
            {
                // 显示灰色
                BlinkDirectionArrow(userDirection, false);
            }
            
            // 闪烁2秒后停止
            if (blinkTimer > 2f)
            {
                isBlinking = false;
                ResetArrowColors();
            }
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

        // 如果用户有当前方向输入，且该方向变为不可行，开始闪烁
        if (userDirection >= 0 && userDirection <= 2 && 
            currentOptions[userDirection] == 0 && userHasInput)
        {
            isBlinking = true;
            blinkTimer = 0f;
        }
        else if (!isBlinking)
        {
            // 如果没有在闪烁，正常设置颜色
            SetArrowColor(leftArrow, currentOptions[0]);
            SetArrowColor(forwardArrow, currentOptions[1]);
            SetArrowColor(rightArrow, currentOptions[2]);
        }

        UpdatePanelState();
    }

    void UserCmdCallback(Int8Msg msg)
    {
        userHasInput = true;
        lastInputTime = Time.time;
        
        // 记录用户输入的方向
        // 假设 msg.data: 0 = 左, 1 = 前进, 2 = 右
        if (msg.data >= 0 && msg.data <= 2)
        {
            userDirection = msg.data;
            
            // 检查所选方向是否可行（对应选项是否为0）
            if (currentOptions[userDirection] == 0)
            {
                // 路径不可行，开始闪烁
                isBlinking = true;
                blinkTimer = 0f;
            }
        }
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
        
        // 当用户输入了不可行的方向时，也显示面板
        if (isBlinking && userDirection >= 0 && userDirection <= 2 && currentOptions[userDirection] == 0)
        {
            showPanel = true;
        }

        arrowPanel.SetActive(showPanel);
    }

    void SetArrowColor(Image arrow, int status)
    {
        if (arrow == null) return;
        arrow.color = (status == 1) ? Color.green : Color.gray;
    }
    
    // 根据方向使箭头闪烁
    void BlinkDirectionArrow(int direction, bool isRed)
    {
        Image targetArrow = null;
        switch (direction)
        {
            case 0: targetArrow = leftArrow; break;
            case 1: targetArrow = forwardArrow; break;
            case 2: targetArrow = rightArrow; break;
        }
        
        if (targetArrow != null)
        {
            // 根据参数设置红色或灰色
            targetArrow.color = isRed ? blinkColor : Color.gray;
        }
    }
    
    // 重置所有箭头颜色为正常状态
    void ResetArrowColors()
    {
        SetArrowColor(leftArrow, currentOptions[0]);
        SetArrowColor(forwardArrow, currentOptions[1]);
        SetArrowColor(rightArrow, currentOptions[2]);
    }
}

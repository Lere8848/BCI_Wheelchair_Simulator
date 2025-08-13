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
    
    // Direction input and path conflict related
    private int userDirection = -1; // -1: no input, 0: left, 1: forward, 2: right
    private bool isBlinking = false; // Whether blinking
    private float blinkTimer = 0f;
    private float blinkInterval = 0.5f; // Blink interval
    private Color blinkColor = Color.red; // Blink color

    // Status flags
    private bool isStopped = false; // Whether wheelchair is stopped
    private bool userHasInput = false; // Whether user has input
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
        // Check if timeout
        if (Time.time - lastInputTime > inputTimeout)
        {
            userHasInput = false;
            // Stop blinking after timeout
            if (isBlinking)
            {
                isBlinking = false;
                ResetArrowColors(); // Restore normal colors
            }
        }

        // If wheelchair is still moving but user has no input for 3 seconds, it means local path is running independently → show panel
        if (!isStopped && !userHasInput)
        {
            arrowPanel.SetActive(true);
        }
        
        // Handle arrow blinking
        if (isBlinking && userDirection >= 0 && userDirection <= 2)
        {
            blinkTimer += Time.deltaTime;
            
            // Control blink frequency
            if (blinkTimer % blinkInterval < blinkInterval * 0.5f)
            {
                // Show red color
                BlinkDirectionArrow(userDirection, true);
            }
            else
            {
                // Show gray color
                BlinkDirectionArrow(userDirection, false);
            }
            
            // Stop blinking after 2 seconds
            if (blinkTimer > 2f)
            {
                isBlinking = false;
                ResetArrowColors();
            }
        }
    }

    void CmdVelCallback(TwistMsg msg)
    {
        // Check if wheelchair is almost stationary (both linear and angular velocities are very small)
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

        // If user has current directional input and that direction becomes infeasible, start blinking
        if (userDirection >= 0 && userDirection <= 2 && 
            currentOptions[userDirection] == 0 && userHasInput)
        {
            isBlinking = true;
            blinkTimer = 0f;
        }
        else if (!isBlinking)
        {
            // If not blinking, set colors normally
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
        
        // Record user input direction
        // Assume msg.data: 0 = left, 1 = forward, 2 = right
        if (msg.data >= 0 && msg.data <= 2)
        {
            userDirection = msg.data;
            
            // Check if selected direction is feasible (corresponding option is not 0)
            if (currentOptions[userDirection] == 0)
            {
                // Path is not feasible, start blinking
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
            showPanel = true; // Always show panel during danger stop (even if no options or only one option)
        }
        else if (isStopped)
        {
            if (openCount >= 2)
                showPanel = true; // Show panel when stopped if two or more options are open
            else if (openCount == 1 && !userHasInput) 
                showPanel = true; // Show panel when stopped if only one option is open and no user input
        } // Otherwise don't show UI abruptly
        
        // Also show panel when user input an infeasible direction
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
    
    // Make arrow blink based on direction
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
            // set arrow color
            targetArrow.color = isRed ? blinkColor : Color.gray;
        }
    }

    // Reset all arrow colors to normal state
    void ResetArrowColors()
    {
        SetArrowColor(leftArrow, currentOptions[0]);
        SetArrowColor(forwardArrow, currentOptions[1]);
        SetArrowColor(rightArrow, currentOptions[2]);
    }
}

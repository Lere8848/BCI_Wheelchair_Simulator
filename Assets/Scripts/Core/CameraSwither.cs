using UnityEngine;

public class CameraManager : MonoBehaviour
{
    public Camera firstPersonCamera; // first person view (attached to player's head)
    public Camera thirdPersonCamera; // third person view (attached to the back of the wheelchair)
    public Camera secondPersonCamera; // second person view (attached to the front of the wheelchair)
    public Camera topDownCamera;     // top-down view (directly above on the Y-axis)
    public Camera diagonalCamera;    // diagonal view (e.g. 45 degrees from back up)

    public TMPro.TextMeshProUGUI cameraStatusText; // UI text to display current view

    void Start()
    {
        // default TPV
        SwitchTo(firstPersonCamera);
        UpdateCameraStatus("TPV");
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.F1))
        {
            Debug.Log("Switched to first person view.");
            SwitchTo(firstPersonCamera);
        }
        else if (Input.GetKeyDown(KeyCode.F2))
        {
            Debug.Log("Switched to third person view.");
            SwitchTo(thirdPersonCamera);
        }
        else if (Input.GetKeyDown(KeyCode.F3))
        {
            Debug.Log("Switched to second person view.");
            SwitchTo(secondPersonCamera);
        }
        else if (Input.GetKeyDown(KeyCode.F4))
        {
            Debug.Log("Switched to top-down view.");
            SwitchTo(topDownCamera);
        }
        else if (Input.GetKeyDown(KeyCode.F5))
        {
            Debug.Log("Switched to diagonal view.");
            SwitchTo(diagonalCamera);
        }
    }

    // switch to the specified camera, disable other cameras, and handle Audio Listener
    void SwitchTo(Camera target)
    {
        Camera[] allCameras = new Camera[] { firstPersonCamera, thirdPersonCamera, secondPersonCamera, topDownCamera, diagonalCamera };
        foreach (Camera cam in allCameras)
        {
            if (cam != null)
            {
                bool isTarget = (cam == target);
                cam.enabled = isTarget;

                // handle Audio Listener
                AudioListener listener = cam.GetComponent<AudioListener>();
                if (listener != null)
                {
                    listener.enabled = isTarget;
                }
            }
        }
    }

    // UI 
    private void UpdateCameraStatus(string name)
    {
        if (cameraStatusText != null)
            cameraStatusText.text = $"current: {name}";
    }

    // method for UI to call
    public void SwitchToView(string viewName)
    {
        Debug.Log("[CameraManager] UI Request to switch to view: " + viewName);
        switch (viewName)
        {
            case "FPV":
                SwitchTo(firstPersonCamera);
                UpdateCameraStatus("FPV");
                Debug.Log("Switched to first person view.");
                break;
            case "TPV":
                SwitchTo(thirdPersonCamera);
                UpdateCameraStatus("TPV");
                Debug.Log("Switched to third person view.");
                break;
            case "SPV":
                SwitchTo(secondPersonCamera);
                UpdateCameraStatus("SPV");
                Debug.Log("Switched to second person view.");
                break;
            case "Top":
                SwitchTo(topDownCamera);
                UpdateCameraStatus("TopDown");
                Debug.Log("Switched to top-down view.");
                break;
            case "Diag":
                SwitchTo(diagonalCamera);
                UpdateCameraStatus("Diagonal");
                Debug.Log("Switched to diagonal view.");
                break;
            default:
                UpdateCameraStatus(" ");
                break;
        }
    }

}

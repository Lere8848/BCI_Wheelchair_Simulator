using UnityEngine;

public class CameraManager : MonoBehaviour
{
    public Camera firstPersonCamera; // 第一人称视角（绑定在玩家头部）
    public Camera thirdPersonCamera; // 第三人称视角（绑定在轮椅后面）
    public Camera secondPersonCamera; // 第二人称视角（绑定在轮椅前面）
    public Camera topDownCamera;     // 俯视图（Y轴正上方）
    public Camera diagonalCamera;    // 斜视图（例如后上45度）

    void Start()
    {
        SwitchTo(thirdPersonCamera);
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

    // 切换到指定相机，禁用其他相机，并处理Audio Listener
    void SwitchTo(Camera target)
    {
        Camera[] allCameras = new Camera[] { firstPersonCamera, thirdPersonCamera, secondPersonCamera, topDownCamera, diagonalCamera };
        foreach (Camera cam in allCameras)
        {
            if (cam != null)
            {
                bool isTarget = (cam == target);
                cam.enabled = isTarget;

                // 处理Audio Listener
                AudioListener listener = cam.GetComponent<AudioListener>();
                if (listener != null)
                {
                    listener.enabled = isTarget;
                }
            }
        }
    }
}

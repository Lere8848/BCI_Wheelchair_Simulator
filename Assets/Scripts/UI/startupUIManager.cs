using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using Unity.Robotics.ROSTCPConnector;
using TMPro;

public class UIManager : MonoBehaviour
{
    public GameObject startupPanel;
    public TextMeshProUGUI rosStatusText;

    void Start()
    {
        startupPanel.SetActive(true);
    }

    public void EnterOfficeScene()
    {
        SceneManager.LoadScene("IndoorOffice");
    }

     public void EntertmpScene()
    {
        SceneManager.LoadScene("tmp");
    }


    public void CheckRosConnection()
    {
        var ros = ROSConnection.GetOrCreateInstance();
        if (ros.HasConnectionThread && !ros.HasConnectionError)
            rosStatusText.text = $"Connected to {ros.RosIPAddress}:{ros.RosPort}";
        else
            rosStatusText.text = "Not connected to ROS2";
    }

    public void ExitApp()
    {
        Application.Quit();
    }
}

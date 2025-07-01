using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System.Reflection;

public class EnableRosHudInOffice : MonoBehaviour
{
    void Start()
    {
        var ros = ROSConnection.GetOrCreateInstance();
        ros.ShowHud = true;

        // 用反射强制调用 InitializeHUD（因为是 private）
        MethodInfo initHud = typeof(ROSConnection).GetMethod("InitializeHUD", BindingFlags.NonPublic | BindingFlags.Instance);
        initHud?.Invoke(ros, null);
    }
}
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using System.Reflection;

public class EnableRosHudInOffice : MonoBehaviour
{
    void Start()
    {
        var ros = ROSConnection.GetOrCreateInstance();
        ros.ShowHud = true;

        // Use reflection to force call InitializeHUD (because it's private)
        MethodInfo initHud = typeof(ROSConnection).GetMethod("InitializeHUD", BindingFlags.NonPublic | BindingFlags.Instance);
        initHud?.Invoke(ros, null);
    }
}
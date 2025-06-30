using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using System;


public class CameraPublisher : MonoBehaviour
{
    public string topicName = "/camera/image_raw";
    public Camera virtualCamera;
    public int width = 320;
    public int height = 240;
    public float publishHz = 5.0f;

    private RenderTexture renderTexture;
    private Texture2D readTexture;
    private ROSConnection ros;
    private float timer;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<ImageMsg>(topicName);

        renderTexture = new RenderTexture(width, height, 24);
        readTexture = new Texture2D(width, height, TextureFormat.RGB24, false);
        virtualCamera.targetTexture = renderTexture;
    }

    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= 1f / publishHz)
        {
            timer = 0f;
            PublishImage();
        }
    }

    void PublishImage()
    {
        RenderTexture.active = renderTexture;
        virtualCamera.Render();
        readTexture.ReadPixels(new Rect(0, 0, width, height), 0, 0);
        readTexture.Apply();
        RenderTexture.active = null;

        byte[] imageData = readTexture.GetRawTextureData(); // RGB data

        ImageMsg imgMsg = new ImageMsg
        {
            header = new RosMessageTypes.Std.HeaderMsg
            {
                frame_id = "camera_frame",
                stamp = new RosMessageTypes.BuiltinInterfaces.TimeMsg()
            },
            height = (uint)height,
            width = (uint)width,
            encoding = "rgb8",
            is_bigendian = 0,
            step = (uint)(width * 3),
            data = imageData
        };

        ros.Publish(topicName, imgMsg);
    }
}


using UnityEngine;

namespace Simulator.SimUtils
{
    public static class SimUtils
    {
        // Box-Muller方法生成标准高斯分布（均值0，方差1）
        public static float GenerateGaussianNoise()
        {
            float u1 = 1.0f - Random.value;
            float u2 = 1.0f - Random.value;
            return Mathf.Sqrt(-2.0f * Mathf.Log(u1)) * Mathf.Cos(2.0f * Mathf.PI * u2);
        }

        // 计算两个Quaternion之间的角速度（单位：rad/s）
        public static Vector3 CalculateAngularVelocity(Quaternion from, Quaternion to, float deltaTime)
        {
            Quaternion delta = to * Quaternion.Inverse(from);
            delta.ToAngleAxis(out float angle, out Vector3 axis);
            if (angle > 180f) angle -= 360f;
            return axis * angle * Mathf.Deg2Rad / deltaTime;
        }
    }
}

#include <Servo.h>

Servo servo1, servo2, servo3, servo4;

// =========================
// 舵机安装偏移
// =========================
int servo_offset2 = 5;
int servo_offset3 = 0;

// =========================
// 当前角度
// =========================
float current1 = 90;
float current2 = 95;
float current3 = 90;
float current4 = 75;

// =========================
// 运动参数
// =========================
float step_size = 1.0;     // 每次移动角度
int move_delay = 20;       // 每步延时(ms)

// =========================
// 缓动函数
// =========================
void smoothMove(
  Servo &servo,
  float &currentAngle,
  float targetAngle
)
{
  if (targetAngle > currentAngle)
  {
    for (
      float a = currentAngle;
      a <= targetAngle;
      a += step_size
    )
    {
      servo.write(a);
      delay(move_delay);
    }
  }
  else
  {
    for (
      float a = currentAngle;
      a >= targetAngle;
      a -= step_size
    )
    {
      servo.write(a);
      delay(move_delay);
    }
  }

  currentAngle = targetAngle;
}

void setup()
{
  Serial.begin(9600);

  servo1.attach(4);
  servo2.attach(5);
  servo3.attach(8);
  servo4.attach(9);

  servo1.write(current1);
  servo2.write(current2);
  servo3.write(current3);
  servo4.write(current4);

  delay(1000);
}

void loop()
{
  if (Serial.available())
  {
    String s = Serial.readStringUntil('\n');

    int c1 = s.indexOf(',');
    int c2 = s.indexOf(',', c1 + 1);
    int c3 = s.indexOf(',', c2 + 1);

    if (c1 > 0 && c2 > c1 && c3 > c2)
    {
      float t1 = s.substring(0, c1).toFloat();

      float t2 =
        s.substring(c1 + 1, c2).toFloat()
        + servo_offset2;

      float t3 =
        s.substring(c2 + 1, c3).toFloat()
        + servo_offset3;

      float t4 =
        s.substring(c3 + 1).toFloat();

      // =========================
      // 限制范围
      // =========================
      t1 = constrain(t1, 0, 180);
      t2 = constrain(t2, 5, 175);
      t3 = constrain(t3, 5, 175);
      t4 = constrain(t4, 30, 100);

      // =========================
      // 平滑运动
      // =========================
      smoothMove(
        servo1,
        current1,
        t1
      );

      smoothMove(
        servo3,
        current3,
        t3
      );

      smoothMove(
        servo2,
        current2,
        t2
      );

      smoothMove(
        servo4,
        current4,
        t4
      );
    }
  }
}
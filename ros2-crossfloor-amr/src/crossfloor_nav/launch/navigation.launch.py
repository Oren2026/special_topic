from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        # 導航系統啟動
        Node(
            package='nav2_bringup',
            executable='navigation_launch',
            name='navigation_launch',
            output='screen',
            parameters=[{'use_sim_time': True}],
        ),
        # SLAM  建圖
        Node(
            package='slam_toolbox',
            executable='online_async_launch',
            name='slam_toolbox',
            output='screen',
            parameters=[{'use_sim_time': True}],
        ),
    ])
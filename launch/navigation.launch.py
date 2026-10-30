#!/usr/bin/env python3
#
# Copyright 2023 6-robot.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors: Zhang Wanjie

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    launch_file_dir = os.path.join(get_package_share_directory('wpr_simulation2'), 'launch')

    home_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_file_dir, 'robocup_home.launch.py')
        )
    )

    behavior_tree = os.path.join(
        get_package_share_directory('wpr_simulation2'),
        'config',
        'behavior_tree.xml'
    )

    map_file = os.path.join(
        get_package_share_directory('wpr_simulation2'),
        'maps',
        'map.yaml'
    )

    nav_param_file = os.path.join(
        get_package_share_directory('wpr_simulation2'),
        'config',
        'nav2_params.yaml'
    )

    nav2_launch_dir = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'launch'
    )

    navigation_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([nav2_launch_dir, '/bringup_launch.py']),
        launch_arguments={
            'map': map_file,
            'use_sim_time': use_sim_time,
            'params_file': nav_param_file}.items(),
    )

    rviz_cmd = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', [os.path.join(get_package_share_directory('wpr_simulation2'), 'rviz', 'navi.rviz')]]
        )

    global_relocalization_cmd = Node(
        package='wpr_simulation2',
        executable='active_global_relocalization.py',
        name='active_global_relocalization',
        output='screen',
        parameters=[nav_param_file, {
            'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
            'active_hypothesis_relocalization': ParameterValue(
                LaunchConfiguration('active_hypothesis_relocalization'), value_type=bool),
            'automatic_relocalization': ParameterValue(
                LaunchConfiguration('automatic_relocalization'), value_type=bool),
            'simulation_odom_validation': ParameterValue(
                LaunchConfiguration('simulation_odom_validation'), value_type=bool),
        }],
    )

    ld = LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'active_hypothesis_relocalization', default_value='false',
            description='Enable experimental multi-hypothesis active disambiguation'),
        DeclareLaunchArgument(
            'automatic_relocalization', default_value='true',
            description='Automatically trigger recovery on localization mismatch'),
        DeclareLaunchArgument(
            'simulation_odom_validation', default_value='true',
            description='Gazebo-only truth guard; disable for algorithm-only evaluation'),
    ])

    # Add the commands to the launch description
    ld.add_action(home_cmd)
    ld.add_action(navigation_cmd)
    ld.add_action(global_relocalization_cmd)
    ld.add_action(rviz_cmd)

    return ld

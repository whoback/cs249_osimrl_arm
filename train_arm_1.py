# This file trains the arm's own muscles
# https://medium.com/@asteinbach/actor-critic-using-deep-rl-continuous-mountain-car-in-tensorflow-4c1fb2110f7c


from osim_rl_master.osim.env.armLocalAct import Arm2DEnv
from osim_rl_master.osim.env.armLocalAct import Arm2DVecEnv

import pprint
import numpy as np
import matplotlib.pyplot as plt
import random

import os
import gym
import sys
from keras.models import Sequential, Model
from keras.layers import Dense, Dropout, Input
from keras.layers.merge import Add, Multiply
from keras.optimizers import Adam
import keras.backend as K
import opensim as osim
import tensorflow as tf

from collections import deque

## Initialize environment & set up networks
env = Arm2DVecEnv(visualize=True, integrator_accuracy=1e-2)

state_dims = env.observation_space.shape[0]
state_placeholder = tf.placeholder(tf.float32, [None, state_dims])
# state_action_placeholder = tf.placeholder(tf.float32, [None, state_dims])


def value_function(state):
    n_hidden1 = 64 
    n_hidden2 = 32
    n_outputs = 1
    
    with tf.variable_scope("value_network"):
        init_xavier = tf.contrib.layers.xavier_initializer() # a method of intializing
        # concat = tf.concat([state, action], axis=0)
        hidden1 = tf.layers.dense(state, n_hidden1, tf.nn.relu, init_xavier)
        hidden2 = tf.layers.dense(hidden1, n_hidden1, tf.nn.relu, init_xavier)
        hidden3 = tf.layers.dense(hidden2, n_hidden1, tf.nn.relu, init_xavier)
        hidden4 = tf.layers.dense(hidden3, n_hidden1, tf.nn.relu, init_xavier)
        hidden5 = tf.layers.dense(hidden4, n_hidden1, tf.nn.relu, init_xavier)
        hidden6 = tf.layers.dense(hidden5, n_hidden1, tf.nn.relu, init_xavier)


        # hidden1_action = tf.layers.dense(action, n_hidden1, tf.nn.relu, init_xavier)
        # hidden2 = hidden1 + hidden1_action
        hidden7 = tf.layers.dense(hidden6, n_hidden2, tf.nn.relu, init_xavier) 
        V = tf.layers.dense(hidden7, n_outputs, tf.compat.v1.keras.activations.linear, init_xavier)
    return V

def policy_network_d(state):
    n_hidden1 = 40
    n_hidden2 = 40
    # n_hidden3 = 40
    # n_hidden4 = 40
    # n_hidden5 = 10
    n_outputs = 8 # hardcoded number of muscles
    
    with tf.variable_scope("policy_network"):
        init_xavier = tf.contrib.layers.xavier_initializer()
        
        hidden1 = tf.layers.dense(state, n_hidden1, tf.nn.relu, init_xavier)
        hidden2 = tf.layers.dense(hidden1, n_hidden2, tf.nn.relu, init_xavier)
        # hidden3 = tf.layers.dense(hidden2, n_hidden2, tf.nn.relu, init_xavier)
        # hidden4 = tf.layers.dense(hidden3, n_hidden2, tf.nn.relu, init_xavier)
        # hidden5 = tf.layers.dense(hidden4, n_hidden2, tf.nn.relu, init_xavier)
        mu = tf.layers.dense(hidden2, n_outputs, tf.nn.sigmoid, init_xavier)

        # stochastic params
        # sigma = tf.layers.dense(hidden2, n_outputs, tf.nn.sigmoid, init_xavier)
        # sigma = tf.nn.softplus(sigma) + 1e-5
        # norm_dist = tf.contrib.distributions.Normal(mu, sigma)
        # action_tf_var = tf.squeeze(norm_dist.sample(1), axis=0)  # remove the batch dimension

        # hard code action space limits
        action_space_low = 0
        action_space_high = 1
        action_tf_var = tf.clip_by_value(
            mu, action_space_low, 
            action_space_high) # this returns a tensor flow variable that can be backpropagated
    # return action_tf_var, norm_dist
    return action_tf_var

# stochastic policy
def policy_network_s(state):
        n_hidden1 = 40
        n_hidden2 = 40
        # n_hidden3 = 40
        # n_hidden4 = 40
        # n_hidden5 = 10
        n_outputs = 8 # 2 actuators
        
        with tf.variable_scope("policy_network_arm"):
            init_xavier = tf.contrib.layers.xavier_initializer()
            
            hidden1 = tf.layers.dense(state, n_hidden1, tf.nn.relu, init_xavier)
            hidden2 = tf.layers.dense(hidden1, n_hidden2, tf.nn.relu, init_xavier)
            hidden3 = tf.layers.dense(hidden2, n_hidden2, tf.nn.relu, init_xavier)
            # hidden4 = tf.layers.dense(hidden3, n_hidden2, tf.nn.relu, init_xavier)
            # hidden5 = tf.layers.dense(hidden4, n_hidden2, tf.nn.relu, init_xavier)
            mu = tf.layers.dense(hidden3, n_outputs, tf.nn.sigmoid, init_xavier)
            sigma = tf.layers.dense(hidden3, n_outputs, tf.nn.sigmoid, init_xavier)
            sigma = tf.nn.softplus(sigma) + 1e-5
            norm_dist = tf.contrib.distributions.Normal(mu, sigma)
            action_tf_var_arm = tf.squeeze(norm_dist.sample(1), axis=0)  # remove the batch dimension

            # hard code action space limits
            action_space_low = 0
            action_space_high = 1
            action_tf_var_arm = tf.clip_by_value(
                action_tf_var_arm, action_space_low, 
                action_space_high) # this returns a tensor flow variable that can be backpropagated
        return action_tf_var_arm, norm_dist


#set learning rates
lr_actor = 0.001  
lr_critic = 0.001

# define required placeholders
action_placeholder = tf.placeholder(tf.float32)
# state_action_placeholder = tf.placeholder(tf.float32)
delta_placeholder = tf.placeholder(tf.float32)
target_placeholder = tf.placeholder(tf.float32)

action_tf_var, norm_dist = policy_network_s(state_placeholder)
# action_tf_var = policy_network_d(state_placeholder)
V = value_function(state_placeholder)

## DEFINE LOSSES

# define actor (policy) loss function
# loss_actor = -tf.log(K.sum(action_tf_var*action_placeholder) + 1e-5) * delta_placeholder

loss_actor_sto = -tf.log(norm_dist.prob(action_placeholder) + 1e-5) * delta_placeholder

loss_actor = tf.reduce_mean(tf.squared_difference(
                             tf.squeeze(action_tf_var), delta_placeholder))

training_op_actor = tf.train.AdamOptimizer(
    lr_actor, name='actor_optimizer').minimize(loss_actor_sto)

# define critic (state-value) loss function
loss_critic = tf.reduce_mean(tf.squared_difference(
                             tf.squeeze(V), target_placeholder))
training_op_critic = tf.train.AdamOptimizer(
        lr_critic, name='critic_optimizer').minimize(loss_critic)


################################################################
#sample from state space for state normalization
import sklearn
import sklearn.preprocessing
                                    
state_space_samples = np.array(
    [env.observation_space.sample() for x in range(10000)])
scaler = sklearn.preprocessing.StandardScaler()
scaler.fit(state_space_samples)

#function to normalize states
def scale_state(state):                 #requires input shape=(2,)
    scaled = scaler.transform([state])
    return scaled                       #returns shape =(1,2)   
###################################################################
###################################################################
# Define fake critic
def fake_critic(state):
    target_x = state[0]
    target_y = state[1]

    pos_x = state[-2]
    pos_y = state[-1]

    penalty = (pos_x - target_x)**2 + (pos_y - target_y)**2
    return -penalty

################################################################
#Training loop
gamma = 0.99        #discount factor
num_episodes = 100
max_step = 500
env.time_limit = max_step
epsilon_init =0.03
epsilon_decline = 0.5
batch_size = 1

# debug code
# env.reset()
# state_desc = env.get_state_desc()
# print(state_desc["joint_pos"]["r_elbow"])
# print(state_desc["markers"])
# act1 = env.action_space.sample()
# env.step(act1)
# print(state_desc)

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    episode_history = []
    episode_steps = []
    episod_dist_r = []
    episod_act_r = []
    for episode in range(num_episodes):
        #receive initial state from E
        goal = env.reset()   # state.shape -> (2,)
        # print(env.get_observation())
        state = np.array(env.get_observation())
        INIT_state = np.array(env.get_observation())

        reward_total = 0 
        steps = 0
        done = False

        # episode_distace =[]
        distance_rewards = 0
        activation_rewards =0

        while (not done) and steps<max_step:
            # select an action
            # print('threshold', epsilon_init*epsilon_decline**episode)
            if np.random.random() > (epsilon_init*epsilon_decline**episode):
                action  = sess.run(action_tf_var, feed_dict={
                              state_placeholder: state.reshape((1, state_dims))})
            else:
                print('took random')
                action = np.array(env.action_space.sample())

            action = action.reshape((1, env.action_space.shape[0])) 
            # print('action is', action)


            # take the action
            next_state, reward, done, info = env.step(
                                    np.squeeze(action, axis=0), obs_as_dict=False)
            _, d_r, act_r = env.get_reward_separate()

            # store rewards
            distance_rewards += d_r
            activation_rewards += act_r
            reward_total += reward
            # if elbow breaks
            if info ==-1:
                reward_total = -1000
                distance_rewards = -500
                activation_rewards = -500

            # print(reward_total)
            next_state = np.array(next_state)

            V_of_next_state = sess.run(V, feed_dict = 
                    {state_placeholder: next_state.reshape((1, state_dims))})  
   
            target = reward + gamma * np.squeeze(V_of_next_state)

            # td_error = target - V(s)
            #needed to feed delta_placeholder in actor training
            td_error = target - np.squeeze(sess.run(V, feed_dict = 
                        {state_placeholder: state.reshape((1, state_dims))})) 

            # td_error = target - fake_critic(state)
            
            if np.mod(steps, batch_size) ==0:
                #Update critic by minimizinf loss  (Critic training)
                _, loss_critic_val  = sess.run(
                    [training_op_critic, loss_critic], 
                    feed_dict={state_placeholder: state.reshape((1, state_dims)), 
                    target_placeholder: target})
                #Update actor by minimizing loss (Actor training)
                _, loss_actor_val  = sess.run(
                    [training_op_actor, loss_actor], 
                    feed_dict={action_placeholder: np.squeeze(action), 
                    state_placeholder: state.reshape((1, state_dims)), 
                    delta_placeholder: td_error})
            
            state = np.array(next_state)

            steps +=1

            #end while

        # plt.plot(episode_distace)
        # plt.show()
        if steps>1:
            episode_history.append(reward_total)
            episod_dist_r.append(distance_rewards)
            episod_act_r.append(activation_rewards)
            episode_steps.append(steps)

        print("Episode: {}, Number of Steps : {}, Average Cumulative reward: {:0.2f}".format(
            episode, steps, reward_total))
        
        # if np.mean(episode_history[-100:]) > 90 and len(episode_history) >= 101:
        #     print("****************Solved***************")
        #     print("Mean cumulative reward over 100 episodes:{:0.2f}" .format(
        #         np.mean(episode_history[-100:])))

# do some ploting
plt.plot(episode_history)
# plt.hold(True)
plt.plot(episod_act_r)
plt.plot(episod_dist_r)
# plt.hold(False)
plt.ylabel('Reward/Step')
plt.xlabel('Episode Number')
plt.legend(['Total Reward', 'Activation Reward', 'Distance Reward'])

plt.show()

plt.plot(episode_steps)
plt.ylabel('Total Steps to Reach Goal')
plt.xlabel('Episodes Number')
plt.show()


import csv

rewards_mat =  np.concatenate([[episode_history], [episod_act_r], [episod_dist_r]])
print(rewards_mat)

    
# Save Numpy array to csv
np.savetxt('a_fixed_reward.csv', rewards_mat, delimiter=',')

np.savetxt('a_fixed_episodelen.csv', episode_steps, delimiter=',')

# with open('filename', 'wb') as myfile:
#     wr = csv.writer(rewards_mat)
#     wr.writerow(mylist)



# Overview
This is a repository for NeurIPS 2025 submission "Learning from Reward-Free Offline Data: A Case for Planning with Latent Dynamics Models".

<img src="assets/main_idea.png" width="100%" style="max-width: 640px"><br/>

In this paper, we focus on methods that can learn from offline trajectories
without reward annotations. We test methods ranging from RL to control, and
find that planning with a learned latent dynamics model (PLDM) is a promising
approach for this setting when the data is imperfect.

# Setting up

## Repo Setup

```
cd PLDM

pip install -r requirements.txt

pip install -e .
```

## Run Experiments

1. Go to `pldm_envs/`, follow instructions to set up dataset for the environment of your hoice
2. Go to `pldm/`, follow instruction to run training or evaluation

## Datasets

To see the datasets we used to train our models, see folders inside `pldm_envs/`.
The readmes there will guide you on how to download and set up the datasets.

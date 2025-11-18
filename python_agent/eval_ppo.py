from train_single_agent import SingleAgentTrainer

if __name__ == "__main__":
    trainer = SingleAgentTrainer(
        agent_type="ppo",
        port=12346,
        name="Player2_PPO_EVAL",
        load_path="models/Player2_PPO_20251117_161824/model_episode_3500.pth"
    )
    trainer.agent.set_eval_mode()
    trainer.train(episodes=1, max_steps=500)
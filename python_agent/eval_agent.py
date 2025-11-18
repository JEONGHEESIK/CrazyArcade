from train_single_agent import SingleAgentTrainer

if __name__ == "__main__":
    trainer = SingleAgentTrainer(
        agent_type="dqn",
        port=12345,
        name="Player1_DQN_EVAL",
        load_path="models/Player1_DQN_20251117_161822/model_episode_3000.pth"
    )
    trainer.agent.set_eval_mode()
    trainer.train(episodes=1, max_steps=500)
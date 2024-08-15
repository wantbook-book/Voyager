async function obtainWoodLog(bot) {
  // Find a tree that contains oak logs
  const tree = await exploreUntil(bot, new Vec3(1, 0, 1), 32, () => {
    const log = bot.findBlock({
      matching: block => block.name === "oak_log",
      maxDistance: 32
    });
    return log;
  });
  if (tree) {
    // Mine one oak log
    await mineBlock(bot, "oak_log", 1);
    bot.chat("Wood log obtained.");
  } else {
    bot.chat("No wood logs nearby.");
  }
}

// Call the function to obtain a wood log
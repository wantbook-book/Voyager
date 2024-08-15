async function mineFiveStoneBlocks(bot) {
  // Find a stone block
  await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
    const stone = bot.findBlock({
      matching: mcData.blocksByName["stone"].id,
      maxDistance: 32
    });
    return stone;
  });

  // Mine 5 stone blocks
  await mineBlock(bot, "stone", 5);
  bot.chat("5 stone blocks mined.");
}
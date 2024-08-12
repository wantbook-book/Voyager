async function mineWoodLog(bot) {
  // Find a wood log block
  const logBlock = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
    const log = bot.findBlock({
      matching: mcData.blocksByName["birch_log"].id,
      maxDistance: 32
    });
    return log;
  });
  if (!logBlock) {
    bot.chat("Could not find a wood log.");
    return;
  }

  // Mine the wood log block
  await mineBlock(bot, logBlock.name, 1);
  bot.chat("Wood log mined.");
}
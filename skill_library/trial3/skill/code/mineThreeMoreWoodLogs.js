async function mineThreeMoreWoodLogs(bot) {
  // Check if the bot has enough oak logs in its inventory
  const oakLogs = bot.inventory.count(mcData.itemsByName["oak_log"].id);
  if (oakLogs < 4) {
    // Mine oak logs until the bot has at least 4
    await mineBlock(bot, "oak_log", 4 - oakLogs);
  }

  // Check if the bot has enough oak planks and sticks in its inventory
  const oakPlanks = bot.inventory.count(mcData.itemsByName["oak_planks"].id);
  const sticks = bot.inventory.count(mcData.itemsByName["stick"].id);
  if (oakPlanks < 3 || sticks < 2) {
    // Craft oak planks and sticks until the bot has at least 3 planks and 2 sticks
    await craftItem(bot, "oak_planks", 3 - oakPlanks);
    await craftItem(bot, "stick", 2 - sticks);
  }

  // Check if there is a crafting table nearby
  const craftingTable = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
    const craftingTable = bot.findBlock({
      matching: mcData.blocksByName["crafting_table"].id,
      maxDistance: 32
    });
    return craftingTable;
  });
  if (!craftingTable) {
    bot.chat("No crafting table nearby");
    return;
  }

  // Craft a wooden axe using the crafting table and the oak planks and sticks
  await craftItem(bot, "wooden_axe", 1, craftingTable.position);

  // Find and mine 3 wood log blocks
  for (let i = 0; i < 3; i++) {
    const woodLogBlock = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
      const woodLog = bot.findBlock({
        matching: block => ["oak_log", "birch_log", "spruce_log", "jungle_log", "acacia_log", "dark_oak_log", "mangrove_log"].includes(block.name),
        maxDistance: 32
      });
      return woodLog;
    });
    if (!woodLogBlock) {
      bot.chat("Could not find a wood log.");
      return;
    }
    await mineBlock(bot, woodLogBlock.name, 1);
  }
  bot.chat("3 more wood logs mined.");
}

// Call the function
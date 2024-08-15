async function mineThreeBirchLogs(bot) {
  // Check if the bot has an axe in its inventory
  const axe = bot.inventory.findInventoryItem(mcData.itemsByName["wooden_axe"].id);
  if (!axe) {
    // Check if the bot has enough oak planks and sticks to craft an axe
    const oakPlanks = bot.inventory.count(mcData.itemsByName["oak_planks"].id);
    const sticks = bot.inventory.count(mcData.itemsByName["stick"].id);
    if (oakPlanks < 3 || sticks < 2) {
      // Craft oak planks and sticks if needed
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
  }

  // Find and mine 3 birch log blocks
  for (let i = 0; i < 3; i++) {
    const birchLogBlock = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
      const birchLog = bot.findBlock({
        matching: block => block.name === "birch_log",
        maxDistance: 32
      });
      return birchLog;
    });
    if (!birchLogBlock) {
      bot.chat("Could not find a birch log.");
      return;
    }
    await mineBlock(bot, "birch_log", 1);
  }
  bot.chat("3 birch logs mined.");
}

// Call the function
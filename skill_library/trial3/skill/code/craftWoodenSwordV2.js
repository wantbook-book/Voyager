async function craftWoodenSword(bot) {
  // Check if there are enough oak logs in the inventory
  const oakLogs = bot.inventory.count(mcData.itemsByName["oak_log"].id);
  if (oakLogs < 2) {
    // Explore until find oak logs
    await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
      const oakLog = bot.findBlock({
        matching: mcData.blocksByName["oak_log"].id,
        maxDistance: 32
      });
      return oakLog;
    });
    // Mine oak logs until there are enough in the inventory
    await mineBlock(bot, "oak_log", 2);
  }

  // Check if there are enough oak planks in the inventory
  const oakPlanks = bot.inventory.count(mcData.itemsByName["oak_planks"].id);
  if (oakPlanks < 2) {
    // Craft oak planks using oak logs
    await craftItem(bot, "oak_planks", 2);
  }

  // Check if there are enough sticks in the inventory
  const sticks = bot.inventory.count(mcData.itemsByName["stick"].id);
  if (sticks < 1) {
    // Craft sticks using oak planks
    await craftItem(bot, "stick", 1);
  }

  // Explore until find a crafting table
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

  // Place the crafting table near the player
  const craftingTablePosition = craftingTable.position;
  await placeItem(bot, "crafting_table", craftingTablePosition);

  // Craft a wooden sword using oak planks and sticks with the crafting table
  await craftItem(bot, "wooden_sword", 1, craftingTablePosition);
  bot.chat("Wooden sword crafted.");
}

// Call the function